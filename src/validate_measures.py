"""Re-derive every published figure from the frozen file, independently.

This script does NOT read matter_ledger.duckdb and does not import anything
from build_conformed.py. It goes back to the frozen snapshot and rebuilds each
certified measure down a separately written path -- the party-name
normalisation is implemented here in SQL rather than in Python, so a bug in one
implementation does not reproduce itself in the other. Then it compares, cell
by cell, against the CSVs the build published.

This is the house pattern: every figure that will ever be published is
independently validated against raw SQL. A measure that only agrees with itself
has not been validated.

Exit 0 means every published cell reconciles. Exit 1 means at least one does
not, and the failing cells are printed. Publish nothing on exit 1.
"""
import pathlib
import sys

import duckdb
import pandas as pd

REPO = pathlib.Path(__file__).resolve().parent.parent
UTF8_TXT = REPO / "data" / "raw" / "cv88on.utf8.txt"
REFDIR = REPO / "data" / "reference"
CONFDIR = REPO / "data" / "conformed"

AS_OF = "2026-08-26"
CONTRACT_NOS = "'110','120','130','140','150','151','152','153','160','190','195','196'"
SENTINEL = "01/01/1900"

# The same normalisation as the build, expressed in SQL rather than Python.
# Written from the rule in governance/subject-matter-filter.md, not by porting
# the other implementation.
NORM = """
regexp_replace(
  regexp_replace(
    regexp_replace(lower(%s), '[^a-z0-9& ]+', ' ', 'g'),
    '\\b(inc|llc|l l c|corp|corporation|co|company|ltd|lp|llp|plc|na|usa|us|holdings|group|the)\\b',
    ' ', 'g'),
  '\\s+', ' ', 'g')
"""


def build_independent_view(con):
    con.execute("""
        CREATE VIEW src AS
        SELECT * FROM read_csv('%s', delim='\t', header=true, all_varchar=true,
                               quote='', escape='', strict_mode=false)
    """ % UTF8_TXT.as_posix())

    # R-04: the same well-formedness test, restated.
    con.execute("""
        CREATE VIEW ok AS SELECT * FROM src
        WHERE COALESCE(STATUSCD,'') IN ('S','L','')
          AND regexp_matches(COALESCE(TAPEYEAR,''), '^[0-9]{4}$')
          AND regexp_matches(COALESCE(FILEDATE,''),
                             '^[0-9]{2}/[0-9]{2}/[0-9]{4}$')
    """)

    con.execute("""
        CREATE TABLE ex_tokens AS
        SELECT match_token FROM read_csv('%s', header=true, all_varchar=true)
    """ % (REFDIR / "excluded_parties.csv").as_posix())

    con.execute("""
        CREATE VIEW in_scope AS
        SELECT *, trim(%s) AS p_n, trim(%s) AS d_n
        FROM ok WHERE NOS IN (%s)
    """ % (NORM % "PLT", NORM % "DEF", CONTRACT_NOS))

    con.execute("""
        CREATE TABLE ex_dockets AS
        SELECT DISTINCT CIRCUIT, DISTRICT, OFFICE, DOCKET
        FROM in_scope s JOIN ex_tokens e
          ON ' ' || s.p_n || ' ' LIKE '% ' || e.match_token || ' %'
          OR ' ' || s.d_n || ' ' LIKE '% ' || e.match_token || ' %'
    """)

    # R-01 grain and R-03 closure, restated.
    con.execute("""
        CREATE TABLE v_fact AS
        WITH kept AS (
          SELECT s.* FROM in_scope s
          WHERE NOT EXISTS (SELECT 1 FROM ex_dockets x
                            WHERE x.CIRCUIT=s.CIRCUIT AND x.DISTRICT=s.DISTRICT
                              AND x.OFFICE=s.OFFICE AND x.DOCKET=s.DOCKET)
        ), typed AS (
          SELECT CIRCUIT, DISTRICT, OFFICE, DOCKET, NOS, DISP, PROCPROG, ORIGIN,
                 CIRCUIT||'-'||DISTRICT||'-'||OFFICE||'-'||DOCKET||'-'||FILEDATE
                   AS matter_key,
                 CAST(TAPEYEAR AS INTEGER) AS sy,
                 strptime(FILEDATE,'%m/%d/%Y')::DATE AS filed,
                 CASE WHEN STATUSCD='S' OR COALESCE(TERMDATE,'') IN ('', ?)
                      THEN NULL
                      ELSE strptime(TERMDATE,'%m/%d/%Y')::DATE END AS termd,
                 CASE WHEN STATUSCD='L' THEN TRUE
                      WHEN STATUSCD='S' THEN FALSE
                      WHEN COALESCE(STATUSCD,'')=''
                           AND COALESCE(TERMDATE,'') NOT IN ('', ?) THEN TRUE
                      ELSE FALSE END AS closed,
                 ROW_NUMBER() OVER () AS rk
          FROM kept
        )
        SELECT *, ROW_NUMBER() OVER (
                   PARTITION BY matter_key
                   ORDER BY sy DESC, termd DESC NULLS LAST,
                            COALESCE(NULLIF(DISP,'-8'), '~') ASC,
                            COALESCE(NULLIF(PROCPROG,'-8'), '~') ASC,
                            COALESCE(NULLIF(ORIGIN,'-8'), '~') ASC,
                            rk ASC) = 1
                 AS latest,
               CASE WHEN closed AND termd IS NOT NULL
                    THEN date_diff('day', filed, termd) END AS days
        FROM typed
    """, [SENTINEL, SENTINEL])


CHECKS = {
    "m02_disposition_mix": ("""
        SELECT DISP AS disposition_code, COUNT(*) AS closed_matters
        FROM v_fact WHERE closed AND latest GROUP BY 1
    """, ["disposition_code", "closed_matters"]),
    "m03_procedural_progress": ("""
        SELECT PROCPROG AS procedural_progress_code, COUNT(*) AS closed_matters,
               MEDIAN(days) AS median_days
        FROM v_fact WHERE closed AND latest GROUP BY 1
    """, ["procedural_progress_code", "closed_matters", "median_days"]),
    "m01_time_to_termination_by_nos": ("""
        SELECT NOS AS nature_of_suit_code, COUNT(*) AS closed_matters,
               MEDIAN(days) AS median_days
        FROM v_fact WHERE closed AND latest AND days IS NOT NULL GROUP BY 1
    """, ["nature_of_suit_code", "closed_matters", "median_days"]),
    "m04_filing_volume_by_year": ("""
        SELECT YEAR(filed) AS filed_year, NOS AS nature_of_suit_code,
               COUNT(DISTINCT matter_key) AS matters_filed
        FROM v_fact WHERE YEAR(filed) BETWEEN 1988 AND 2026 GROUP BY 1, 2
    """, ["filed_year", "nature_of_suit_code", "matters_filed"]),
    "m05_open_inventory_aging": ("""
        SELECT CASE WHEN a < 365 THEN '0 - under 1 year'
                    WHEN a < 730 THEN '1 - 1 to 2 years'
                    WHEN a < 1095 THEN '2 - 2 to 3 years'
                    WHEN a < 1825 THEN '3 - 3 to 5 years'
                    ELSE '4 - over 5 years' END AS age_band,
               COUNT(*) AS open_matters
        FROM (SELECT date_diff('day', filed, DATE '%s') AS a
              FROM v_fact WHERE NOT closed AND latest) t
        GROUP BY 1
    """ % AS_OF, ["age_band", "open_matters"]),
}


def main():
    if not UTF8_TXT.exists():
        sys.exit("data/raw/cv88on.utf8.txt missing. Run src/build_conformed.py.")
    con = duckdb.connect()
    build_independent_view(con)

    failures = 0
    for name, (sql, cols) in CHECKS.items():
        published = pd.read_csv(CONFDIR / (name + ".csv"))
        derived = con.sql(sql).to_df()
        keys = (cols[:2] if name == "m04_filing_volume_by_year" else cols[:1])
        # The CSV round-trip types a code column as int64 where DuckDB hands
        # back a string. Compare keys as text on both sides so the join is
        # about the values, not about how each path happened to type them.
        pub = published[cols].copy()
        der = derived[cols].copy()
        for k in keys:
            pub[k] = pub[k].astype(str)
            der[k] = der[k].astype(str)
        merged = pub.merge(der, on=keys, how="outer",
                           suffixes=("_published", "_independent"),
                           indicator=True)

        bad = merged[merged["_merge"] != "both"]
        for col in cols[len(keys):]:
            a = merged[col + "_published"]
            b = merged[col + "_independent"]
            mismatch = merged[~((a == b) | (a.isna() & b.isna()))]
            bad = pd.concat([bad, mismatch]).drop_duplicates()

        if len(bad):
            failures += len(bad)
            print("FAIL %-34s %d cells do not reconcile" % (name, len(bad)))
            print(bad.to_string(index=False)[:1800])
        else:
            print("PASS %-34s %d rows reconcile exactly"
                  % (name, len(published)))

    con.close()
    print("\nVALIDATION %s" % ("PASSED" if not failures else "FAILED"))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
