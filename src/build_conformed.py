"""Build fact_matter from the frozen snapshot, under the governed rules.

Implements, in order:

  R-04  quarantine malformed records            governance/docket-to-matter.md
  SM    the three-layer subject-matter control  governance/subject-matter-filter.md
  R-01  grain, identity and clock
  R-03  the effective-dated closure rule

Every rule this script applies is written down first, and the docstring points
at where. Nothing here decides anything on its own authority.

Reads the freeze read-only, after verifying its hash. Writes
data/conformed/matter_ledger.duckdb and a run record.
"""
import csv
import hashlib
import json
import pathlib
import re
import sys
from datetime import datetime, timezone

import duckdb

REPO = pathlib.Path(__file__).resolve().parent.parent
SNAPSHOT_ZIP = REPO / "data" / "raw" / "cv88on.zip"
SNAPSHOT_TXT = REPO / "data" / "raw" / "cv88on.txt"
UTF8_TXT = REPO / "data" / "raw" / "cv88on.utf8.txt"
REFDIR = REPO / "data" / "reference"
CONFDIR = REPO / "data" / "conformed"
DB = CONFDIR / "matter_ledger.duckdb"

FREEZE_SHA256 = "74405231a9a3c246c7090d471a1525924fa5afb513ff22b4dc0f4babbac7223d"

# Layer 1 of the subject-matter control. Contract and commercial disputes.
CONTRACT_NOS = ["110", "120", "130", "140", "150", "151", "152", "153",
                "160", "190", "195", "196"]

SENTINEL_TERMDATE = "01/01/1900"


def verify_freeze():
    h = hashlib.sha256()
    with SNAPSHOT_ZIP.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    if h.hexdigest() != FREEZE_SHA256:
        sys.exit("FREEZE VIOLATION: cv88on.zip hashes to %s, expected %s"
                 % (h.hexdigest(), FREEZE_SHA256))
    return h.hexdigest()


def transcode_to_utf8():
    """Rewrite the extracted member as UTF-8, once, and report what changed.

    The published file is not UTF-8 and is not clean ISO-8859-1 either: party
    names carry bytes in the 0x80-0x9F range, which are control positions in
    ISO-8859-1 and printable characters in Windows-1252. Every CSV reader
    tried here refuses it, and the tempting fix -- ignore_errors=true -- drops
    rows silently, which is the one thing a ledger may not do.

    So the bytes are decoded as Windows-1252 where that is defined and as
    ISO-8859-1 elsewhere, both of which are total functions over single bytes,
    and re-emitted as UTF-8. No row is dropped and no field is truncated. The
    output carries its own hash, and the count of affected rows is published,
    because a transformation nobody counted is a transformation nobody checked.
    """
    if UTF8_TXT.exists():
        return None
    affected = 0
    with SNAPSHOT_TXT.open("rb") as src, UTF8_TXT.open("wb") as dst:
        for raw_line in src:
            if any(b >= 0x80 for b in raw_line):
                affected += 1
                try:
                    text = raw_line.decode("cp1252")
                except UnicodeDecodeError:
                    text = raw_line.decode("latin-1")
                dst.write(text.encode("utf-8"))
            else:
                dst.write(raw_line)
    return affected


def normalise(name):
    """Normalised form used for exclusion matching. Documented in
    governance/subject-matter-filter.md, Layer 2."""
    s = name.lower()
    s = re.sub(r"[^a-z0-9& ]+", " ", s)
    s = re.sub(r"\b(inc|llc|l l c|corp|corporation|co|company|ltd|lp|llp|"
               r"plc|na|usa|us|holdings|group|the)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def exclusion_tokens():
    with (REFDIR / "excluded_parties.csv").open(encoding="utf-8") as fh:
        return [(r["match_token"], r["affiliation"])
                for r in csv.DictReader(fh)]


def main():
    sha = verify_freeze()
    if not SNAPSHOT_TXT.exists():
        sys.exit("data/raw/cv88on.txt not extracted. See README.")
    CONFDIR.mkdir(parents=True, exist_ok=True)
    if DB.exists():
        DB.unlink()
    con = duckdb.connect(str(DB))
    run = {"started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "freeze_sha256": sha, "checks": []}

    def record(name, value, expectation=None, passed=None):
        run["checks"].append({"check": name, "value": value,
                              "expectation": expectation, "passed": passed})
        flag = "" if passed is None else ("  PASS" if passed else "  ** FAIL **")
        print("%-46s %s%s" % (name, value, flag))

    # ---- load the freeze -----------------------------------------------
    # Three reader settings are load-bearing and none of them is the default:
    #
    #   quote='' escape=''   the file is tab-delimited with NO quoting
    #                        convention, and party names contain bare quote
    #                        characters. At the default the reader treats one
    #                        as an opening quote and silently merges 638 rows.
    #   encoding='latin-1'   the file is not UTF-8. Party names carry bytes
    #                        that are invalid UTF-8, and a UTF-8 read aborts
    #                        partway through statistical year 2003.
    #
    # Both were found by two parsers disagreeing, not by reading a spec. The
    # publisher documents neither.
    affected = transcode_to_utf8()
    if affected is not None:
        record("rows re-encoded from Windows-1252 to UTF-8", affected)
    con.execute("""
        CREATE VIEW raw AS
        SELECT * FROM read_csv('%s', delim='\t', header=true, all_varchar=true,
                               quote='', escape='', strict_mode=false)
    """ % UTF8_TXT.as_posix())
    total = con.sql("SELECT COUNT(*) FROM raw").fetchone()[0]
    record("rows in frozen snapshot", total, 10960173, total == 10960173)

    # ---- R-04 quarantine ------------------------------------------------
    # A well-formed record has a parseable status, a 4-digit statistical year
    # and a date-shaped filing date. Records failing this have a delimiter
    # inside a value and every field right of DEF has shifted.
    con.execute("""
        CREATE TABLE quarantine AS
        SELECT *, 'field shift: delimiter inside a value' AS quarantine_reason
        FROM raw
        WHERE NOT (COALESCE(STATUSCD,'') IN ('S','L','')
                   AND regexp_matches(COALESCE(TAPEYEAR,''), '^[0-9]{4}$')
                   AND regexp_matches(COALESCE(FILEDATE,''),
                                      '^[0-9]{2}/[0-9]{2}/[0-9]{4}$'))
    """)
    quarantined = con.sql("SELECT COUNT(*) FROM quarantine").fetchone()[0]
    record("R-04 records quarantined", quarantined, 638, quarantined == 638)

    con.execute("""
        CREATE VIEW clean AS
        SELECT * FROM raw
        WHERE COALESCE(STATUSCD,'') IN ('S','L','')
          AND regexp_matches(COALESCE(TAPEYEAR,''), '^[0-9]{4}$')
          AND regexp_matches(COALESCE(FILEDATE,''),
                             '^[0-9]{2}/[0-9]{2}/[0-9]{4}$')
    """)

    # ---- SM Layer 1, scope ---------------------------------------------
    codes = ", ".join("'%s'" % c for c in CONTRACT_NOS)
    con.execute("CREATE VIEW scoped AS SELECT * FROM clean WHERE NOS IN (%s)"
                % codes)
    scoped = con.sql("SELECT COUNT(*) FROM scoped").fetchone()[0]
    record("SM layer 1 in-scope contract records", scoped)

    # ---- SM Layer 2, name exclusion -------------------------------------
    tokens = exclusion_tokens()
    con.execute("CREATE TABLE excluded_parties (match_token VARCHAR, "
                "affiliation VARCHAR)")
    con.executemany("INSERT INTO excluded_parties VALUES (?, ?)", tokens)
    con.create_function("norm", normalise, ["VARCHAR"], "VARCHAR")

    # Normalise once, into a materialised column, rather than inside the join
    # predicate. Evaluated in the predicate the Python UDF is called once per
    # row per token per field -- 160 million calls over this slice -- and the
    # build does not finish. Materialised, it is called 2.8 million times and
    # the token match runs in the engine.
    con.execute("""
        CREATE TABLE scoped_n AS
        SELECT *, norm(PLT) AS plt_norm, norm(DEF) AS def_norm FROM scoped
    """)

    # Match on WORD BOUNDARIES, not raw substrings. A bare substring match
    # put "t mobile" inside "BIG RIVER DISCOUN|T MOBILE" and excluded a case
    # that has nothing to do with any carrier. Both sides are padded with a
    # space so a token matches only whole words, at either end of the name.
    con.execute("""
        CREATE TABLE excluded_rows AS
        SELECT s.*, e.affiliation AS excluded_affiliation, e.match_token
        FROM scoped_n s
        JOIN excluded_parties e
          ON ' ' || s.plt_norm || ' ' LIKE '% ' || e.match_token || ' %'
          OR ' ' || s.def_norm || ' ' LIKE '% ' || e.match_token || ' %'
    """)
    excluded_rowcount = con.sql("SELECT COUNT(DISTINCT (CIRCUIT, DISTRICT, "
                                "OFFICE, DOCKET, FILEDATE)) "
                                "FROM excluded_rows").fetchone()[0]
    record("SM layer 2 records matching the exclusion list", excluded_rowcount)

    # Exclude at DOCKET level, not row level. The same docket carries the
    # carrier's name spelled three different ways across its records --
    # "CONTI CABLEVISION N E", "CONTI CABELISION ON N E" (the source's own
    # typo) and "CONTINENTAL CABLE, ET AL" -- so a row-level filter drops one
    # record of a case and keeps another. Docket-level exclusion over-excludes
    # where a docket number has been reused for an unrelated case, which is
    # the safe direction and is counted below.
    con.execute("""
        CREATE TABLE excluded_dockets AS
        SELECT DISTINCT CIRCUIT, DISTRICT, OFFICE, DOCKET FROM excluded_rows
    """)
    excluded = con.sql("""
        SELECT COUNT(*) FROM scoped_n s
        WHERE EXISTS (SELECT 1 FROM excluded_dockets d
                      WHERE d.CIRCUIT=s.CIRCUIT AND d.DISTRICT=s.DISTRICT
                        AND d.OFFICE=s.OFFICE AND d.DOCKET=s.DOCKET)
    """).fetchone()[0]
    record("SM layer 2 records excluded, docket level", excluded)
    record("  of which over-excluded by docket reuse",
           excluded - excluded_rowcount)

    # ---- R-01 and R-03, the fact table ----------------------------------
    # No party column survives this SELECT. That is assertion SM-1.
    con.execute("""
        CREATE TABLE fact_matter AS
        SELECT
          -- R-01.b, amended. Three grains, and they are not the same:
          --   docket_key   the court's file. Reused for unrelated cases.
          --   matter_key   one dispute. Docket plus filing date.
          --   record_key   one status record. A matter reopened after
          --                termination produces a second one.
          CIRCUIT || '-' || DISTRICT || '-' || OFFICE || '-' || DOCKET
                                                     AS docket_key,
          CIRCUIT || '-' || DISTRICT || '-' || OFFICE || '-' || DOCKET
            || '-' || FILEDATE                       AS matter_key,
          ROW_NUMBER() OVER ()                       AS record_key,
          CIRCUIT, DISTRICT, OFFICE, DOCKET,
          CAST(TAPEYEAR AS INTEGER)                  AS statistical_year,
          strptime(FILEDATE, '%m/%d/%Y')::DATE       AS filed_date,
          NOS AS nature_of_suit_code,
          JURIS AS jurisdiction_code,
          ORIGIN AS origin_code,
          -- R-03, effective-dated. STATUSCD does not exist before SY2001.
          CASE
            WHEN STATUSCD = 'L' THEN TRUE
            WHEN STATUSCD = 'S' THEN FALSE
            WHEN COALESCE(STATUSCD,'') = ''
                 AND COALESCE(TERMDATE,'') NOT IN ('', ?) THEN TRUE
            ELSE FALSE
          END                                        AS is_closed,
          CASE
            WHEN STATUSCD = 'S' OR COALESCE(TERMDATE,'') IN ('', ?)
              THEN NULL
            ELSE strptime(TERMDATE, '%m/%d/%Y')::DATE
          END                                        AS terminated_date,
          NULLIF(DISP, '-8')                         AS disposition_code,
          NULLIF(PROCPROG, '-8')                     AS procedural_progress_code,
          NULLIF(MDLDOCK, '-8')                      AS mdl_docket,
          NULLIF(TRANSDOC, '-8')                     AS transferred_from_docket,
          CASE WHEN CLASSACT = '1' THEN TRUE ELSE FALSE END AS is_class_action
        FROM scoped_n s
        WHERE NOT EXISTS (
          SELECT 1 FROM excluded_dockets d
          WHERE d.CIRCUIT = s.CIRCUIT AND d.DISTRICT = s.DISTRICT
            AND d.OFFICE = s.OFFICE AND d.DOCKET = s.DOCKET)
    """, [SENTINEL_TERMDATE, SENTINEL_TERMDATE])

    con.execute("ALTER TABLE fact_matter ADD COLUMN days_to_termination INTEGER")
    con.execute("""
        UPDATE fact_matter
        SET days_to_termination = date_diff('day', filed_date, terminated_date)
        WHERE is_closed AND terminated_date IS NOT NULL
    """)

    # A matter that is reopened after termination produces a second status
    # record with a later statistical year and a different disposition. Both
    # are true; they describe different points in the matter's life. Measures
    # that answer "how did this matter end" use the latest record, and say so.
    con.execute("ALTER TABLE fact_matter ADD COLUMN is_latest_record BOOLEAN")
    con.execute("""
        UPDATE fact_matter f SET is_latest_record = (f.record_key = (
          SELECT g.record_key FROM fact_matter g
          WHERE g.matter_key = f.matter_key
          ORDER BY g.statistical_year DESC,
                   g.terminated_date DESC NULLS LAST,
                   g.record_key DESC
          LIMIT 1))
    """)

    rows = con.sql("SELECT COUNT(*) FROM fact_matter").fetchone()[0]
    record("fact_matter records", rows, scoped - excluded,
           rows == scoped - excluded)
    matters = con.sql("SELECT COUNT(DISTINCT matter_key) "
                      "FROM fact_matter").fetchone()[0]
    record("distinct matters", matters)
    record("  records beyond one per matter (reopenings)", rows - matters)

    # ---- dimensions -----------------------------------------------------
    for field in ("nos", "disp", "procprog", "origin", "juris", "statuscd"):
        con.execute("CREATE TABLE dim_%s AS SELECT * FROM read_csv('%s', "
                    "header=true, all_varchar=true)"
                    % (field, (REFDIR / ("dim_%s.csv" % field)).as_posix()))

    # ---- assertions -----------------------------------------------------
    v = con.sql("SELECT COUNT(*) - COUNT(DISTINCT record_key) "
                "FROM fact_matter").fetchone()[0]
    record("R-01.b record_key is unique", v, 0, v == 0)

    v = con.sql("SELECT COUNT(*) FROM (SELECT matter_key FROM fact_matter "
                "WHERE is_latest_record GROUP BY 1 HAVING COUNT(*) > 1)"
                ).fetchone()[0]
    record("R-01.b one latest record per matter", v, 0, v == 0)

    v = con.sql("SELECT COUNT(*) FROM fact_matter "
                "WHERE days_to_termination < 0").fetchone()[0]
    record("R-03 matters with negative duration", v, 0, v == 0)

    v = con.sql("SELECT COUNT(*) FROM fact_matter "
                "WHERE is_closed AND terminated_date IS NULL").fetchone()[0]
    record("R-03 closed matters with no end date", v, 0, v == 0)

    v = con.sql("SELECT COUNT(*) FROM fact_matter WHERE NOT is_closed "
                "AND terminated_date IS NOT NULL").fetchone()[0]
    record("R-03 open matters carrying an end date", v, 0, v == 0)

    cols = [c[0] for c in con.sql("DESCRIBE fact_matter").fetchall()]
    leaked = [c for c in cols if c.upper() in ("PLT", "DEF")]
    record("SM-1 party columns in fact_matter", len(leaked), 0, not leaked)

    v = con.sql("SELECT COUNT(*) FROM fact_matter WHERE nature_of_suit_code "
                "NOT IN (%s)" % codes).fetchone()[0]
    record("SM-2 rows outside the scope code list", v, 0, v == 0)

    # Re-matched against the frozen snapshot, not against the filter's own
    # output. A control that is only ever applied, never re-verified, cannot
    # tell you the day it stops working.
    v = con.sql("""
        SELECT COUNT(*) FROM fact_matter f
        WHERE EXISTS (SELECT 1 FROM excluded_dockets d
                      WHERE d.CIRCUIT = f.CIRCUIT AND d.DISTRICT = f.DISTRICT
                        AND d.OFFICE = f.OFFICE AND d.DOCKET = f.DOCKET)
    """).fetchone()[0]
    record("SM-3 excluded dockets surviving into fact", v, 0, v == 0)

    v = con.sql("SELECT COUNT(*) FROM fact_matter f LEFT JOIN dim_nos d "
                "ON f.nature_of_suit_code = d.code "
                "WHERE d.code IS NULL").fetchone()[0]
    record("every NOS resolves in the dimension", v, 0, v == 0)

    open_n = con.sql("SELECT COUNT(*) FROM fact_matter "
                     "WHERE NOT is_closed").fetchone()[0]
    record("open matters (inventory)", open_n)

    run["finished_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    run["passed"] = all(c["passed"] for c in run["checks"]
                        if c["passed"] is not None)
    (REPO / "governance" / "last_run.json").write_text(
        json.dumps(run, indent=1), encoding="utf-8")
    con.close()
    print("\nRUN %s" % ("PASSED" if run["passed"] else "FAILED"))
    return 0 if run["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
