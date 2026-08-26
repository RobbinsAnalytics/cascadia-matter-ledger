"""Compute the certified measures from fact_matter.

Every measure here has a written definition, a named owner and stated source
lineage in governance/metric_register.md. Nothing is published from this script
that is not defined there, and nothing is defined there that this script does
not compute.

Outputs are small and are committed. They are the figures a frontend renders.
Each is independently re-derived from the frozen file by
src/validate_measures.py before anything may be published.
"""
import json
import pathlib
import sys
from datetime import datetime, timezone

import duckdb

REPO = pathlib.Path(__file__).resolve().parent.parent
DB = REPO / "data" / "conformed" / "matter_ledger.duckdb"
OUT = REPO / "data" / "conformed"

# The as-of date for every age calculation. The snapshot's retrieval date, not
# today's date: an open matter's age is measured against the moment the record
# was captured, otherwise the figure drifts every time someone runs the script.
AS_OF = "2026-08-26"

MEASURES = {
    # M-01 -- Time to termination. Closed matters only, latest record only.
    "m01_time_to_termination_by_nos": """
        SELECT f.nature_of_suit_code            AS nature_of_suit_code,
               d.description                    AS nature_of_suit,
               COUNT(*)                         AS closed_matters,
               MEDIAN(f.days_to_termination)    AS median_days,
               QUANTILE_CONT(f.days_to_termination, 0.25) AS p25_days,
               QUANTILE_CONT(f.days_to_termination, 0.75) AS p75_days
        FROM fact_matter f
        JOIN dim_nos d ON d.code = f.nature_of_suit_code
        WHERE f.is_closed AND f.is_latest_record
          AND f.days_to_termination IS NOT NULL
        GROUP BY 1, 2 ORDER BY closed_matters DESC
    """,
    "m01_time_to_termination_by_court": """
        SELECT f.CIRCUIT || '-' || f.DISTRICT   AS court_code,
               COUNT(*)                         AS closed_matters,
               MEDIAN(f.days_to_termination)    AS median_days
        FROM fact_matter f
        WHERE f.is_closed AND f.is_latest_record
          AND f.days_to_termination IS NOT NULL
        GROUP BY 1 HAVING COUNT(*) >= 1000
        ORDER BY median_days DESC
    """,
    # M-02 -- Disposition mix. How matters end.
    "m02_disposition_mix": """
        SELECT f.disposition_code               AS disposition_code,
               d.description                    AS disposition,
               COUNT(*)                         AS closed_matters,
               ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct
        FROM fact_matter f
        LEFT JOIN dim_disp d ON d.code = f.disposition_code
        WHERE f.is_closed AND f.is_latest_record
        GROUP BY 1, 2 ORDER BY closed_matters DESC
    """,
    # M-03 -- Procedural progress at termination. How far a matter travels.
    "m03_procedural_progress": """
        SELECT f.procedural_progress_code       AS procedural_progress_code,
               d.qualified_description          AS procedural_progress,
               d."group"                        AS issue_joined_group,
               COUNT(*)                         AS closed_matters,
               ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct,
               MEDIAN(f.days_to_termination)    AS median_days
        FROM fact_matter f
        LEFT JOIN dim_procprog d ON d.code = f.procedural_progress_code
        WHERE f.is_closed AND f.is_latest_record
        GROUP BY 1, 2, 3 ORDER BY closed_matters DESC
    """,
    # M-04 -- Filing volume trend. All records, by the year of filing.
    "m04_filing_volume_by_year": """
        SELECT YEAR(f.filed_date)               AS filed_year,
               f.nature_of_suit_code            AS nature_of_suit_code,
               COUNT(DISTINCT f.matter_key)     AS matters_filed
        FROM fact_matter f
        WHERE YEAR(f.filed_date) BETWEEN 1988 AND 2026
        GROUP BY 1, 2 ORDER BY 1, 2
    """,
    # M-05 -- Open inventory and aging, as at the snapshot's as-of date.
    "m05_open_inventory_aging": """
        SELECT CASE
                 WHEN age_days < 365 THEN '0 - under 1 year'
                 WHEN age_days < 730 THEN '1 - 1 to 2 years'
                 WHEN age_days < 1095 THEN '2 - 2 to 3 years'
                 WHEN age_days < 1825 THEN '3 - 3 to 5 years'
                 ELSE '4 - over 5 years'
               END                              AS age_band,
               COUNT(*)                         AS open_matters,
               ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct
        FROM (SELECT date_diff('day', filed_date, DATE '%s') AS age_days
              FROM fact_matter
              WHERE NOT is_closed AND is_latest_record) t
        GROUP BY 1 ORDER BY 1
    """ % AS_OF,
}


def main():
    if not DB.exists():
        sys.exit("data/conformed/matter_ledger.duckdb missing. "
                 "Run src/build_conformed.py first.")
    con = duckdb.connect(str(DB), read_only=True)
    manifest = {
        "built_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "as_of_date": AS_OF,
        "measures": {},
    }
    for name, sql in MEASURES.items():
        df = con.sql(sql).to_df()
        path = OUT / (name + ".csv")
        df.to_csv(path, index=False, lineterminator="\n")
        manifest["measures"][name] = {"rows": len(df),
                                      "columns": list(df.columns)}
        print("%-38s %6d rows" % (name, len(df)))
    (OUT / "measures_manifest.json").write_text(
        json.dumps(manifest, indent=1), encoding="utf-8")
    con.close()


if __name__ == "__main__":
    main()
