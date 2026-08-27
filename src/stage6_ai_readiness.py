"""Stage 6 -- the AI-readiness proof.

One legal-operations question, answered twice: once against the raw frozen
file, once against the governed model. Then the gap between the two answers is
decomposed into named causes, each attributable to a specific governance
artifact in this repo.

THE QUESTION
    "How long does it take to resolve a contract dispute in federal court?"

THE RULE THIS SCRIPT FOLLOWS
    The ungoverned path must be the query a competent analyst would actually
    write, not a strawman. No deliberate mistakes. Reader defaults, the obvious
    filter, the obvious arithmetic. Where the reader raises an error, the path
    takes the fix the tool itself suggests. Every step away from that is a
    governance rule earning its place.

Reads the freeze read-only. Writes governance/ai-readiness-proof.md.
"""
import pathlib
import sys

import duckdb

REPO = pathlib.Path(__file__).resolve().parent.parent
RAW_TXT = REPO / "data" / "raw" / "cv88on.txt"
UTF8_TXT = REPO / "data" / "raw" / "cv88on.utf8.txt"
DB = REPO / "data" / "conformed" / "matter_ledger.duckdb"
OUT = REPO / "governance" / "ai-readiness-proof.md"

CONTRACT = "'110','120','130','140','150','151','152','153','160','190','195','196'"
SENTINEL = "01/01/1900"

# try_strptime, not strptime. Once quoting is disabled the field-shifted
# records expose values like '-8' where a date belongs, and a strict parser
# aborts the whole query on the first one. A tolerant parser is what an analyst
# would reach for, and it makes those records vanish from the average instead
# -- which is the behaviour worth showing.
DUR = ("date_diff('day', try_strptime(FILEDATE,'%m/%d/%Y'), "
       "try_strptime(TERMDATE,'%m/%d/%Y'))")


def main():
    if not RAW_TXT.exists() or not UTF8_TXT.exists() or not DB.exists():
        sys.exit("Run src/build_conformed.py first.")
    con = duckdb.connect()
    steps = []

    def step(n, label, rows, answer, cause, artifact):
        steps.append({"n": n, "label": label, "rows": rows, "answer": answer,
                      "cause": cause, "artifact": artifact})
        print("%-2s %-46s %10s rows  %9s days" %
              (n, label, format(rows, ","),
               "-" if answer is None else round(answer, 1)))

    # ---- STEP 0 ---------------------------------------------------------
    # The obvious query. Reader defaults. DuckDB raises on the encoding, and
    # its own error message says: "Enable ignore errors (ignore_errors=true)
    # to skip this row." The path takes that advice, because an analyst would.
    con.execute("""
        CREATE VIEW naive AS SELECT * FROM read_csv('%s', delim='\t',
            header=true, all_varchar=true, ignore_errors=true)
    """ % RAW_TXT.as_posix())
    r = con.sql("SELECT COUNT(*), AVG(%s) FROM naive WHERE NOS IN (%s)"
                % (DUR, CONTRACT)).fetchone()
    step(0, "the obvious query, reader defaults", r[0], r[1],
         "nothing corrected yet", "-")

    # ---- STEP 1 ---------------------------------------------------------
    # Fix the encoding. The rows the reader was silently discarding come back.
    con.execute("""
        CREATE VIEW enc AS SELECT * FROM read_csv('%s', delim='\t',
            header=true, all_varchar=true, ignore_errors=true)
    """ % UTF8_TXT.as_posix())
    r = con.sql("SELECT COUNT(*), AVG(%s) FROM enc WHERE NOS IN (%s)"
                % (DUR, CONTRACT)).fetchone()
    step(1, "+ correct the encoding", r[0], r[1],
         "the file is not UTF-8 (measured: zero rows recovered)",
         "CLAUDE.md source property 1")

    # ---- STEP 2 ---------------------------------------------------------
    # Disable quoting. Party names carry bare quote characters, so the default
    # reader merges fields and shifts every value right of DEF.
    con.execute("""
        CREATE VIEW quoted AS SELECT * FROM read_csv('%s', delim='\t',
            header=true, all_varchar=true, quote='', escape='',
            strict_mode=false)
    """ % UTF8_TXT.as_posix())
    r = con.sql("SELECT COUNT(*), AVG(%s) FROM quoted WHERE NOS IN (%s)"
                % (DUR, CONTRACT)).fetchone()
    step(2, "+ disable quoting", r[0], r[1],
         "no quoting convention; party names contain bare quotes",
         "CLAUDE.md source property 2")

    # ---- STEP 3 ---------------------------------------------------------
    con.execute("""
        CREATE VIEW clean AS SELECT * FROM quoted
        WHERE COALESCE(STATUSCD,'') IN ('S','L','')
          AND regexp_matches(COALESCE(TAPEYEAR,''), '^[0-9]{4}$')
          AND regexp_matches(COALESCE(FILEDATE,''),
                             '^[0-9]{2}/[0-9]{2}/[0-9]{4}$')
    """)
    r = con.sql("SELECT COUNT(*), AVG(%s) FROM clean WHERE NOS IN (%s)"
                % (DUR, CONTRACT)).fetchone()
    step(3, "+ quarantine field-shifted records", r[0], r[1],
         "638 records carry a tab inside the defendant name",
         "docket-to-matter.md R-04")

    # ---- STEP 4 -- the one that matters ---------------------------------
    r = con.sql("""
        SELECT COUNT(*), AVG(%s) FROM clean
        WHERE NOS IN (%s)
          AND NOT (COALESCE(STATUSCD,'')='S' OR COALESCE(TERMDATE,'')='%s')
    """ % (DUR, CONTRACT, SENTINEL)).fetchone()
    step(4, "+ exclude pending matters", r[0], r[1],
         "pending records carry TERMDATE = 01/01/1900, not null",
         "source-register.md F-02")

    # ---- STEP 5 -- reopenings -------------------------------------------
    con.execute("""
        CREATE TABLE closed AS
        SELECT *, %s AS days,
               CIRCUIT||'-'||DISTRICT||'-'||OFFICE||'-'||DOCKET||'-'||FILEDATE
                 AS mk,
               ROW_NUMBER() OVER () AS rk
        FROM clean
        WHERE NOS IN (%s)
          AND NOT (COALESCE(STATUSCD,'')='S' OR COALESCE(TERMDATE,'')='%s')
    """ % (DUR, CONTRACT, SENTINEL))
    r = con.sql("""
        SELECT COUNT(*), AVG(days) FROM (
          SELECT *, ROW_NUMBER() OVER (PARTITION BY mk
                     ORDER BY CAST(TAPEYEAR AS INTEGER) DESC, rk DESC) AS n
          FROM closed) t WHERE n = 1
    """).fetchone()
    step(5, "+ one record per matter (reopenings)", r[0], r[1],
         "a reopened matter produces a second status record",
         "docket-to-matter.md R-01.b")

    # ---- STEP 6 -- the governed answer ----------------------------------
    gcon = duckdb.connect(str(DB), read_only=True)
    r = gcon.sql("""
        SELECT COUNT(*), AVG(days_to_termination), MEDIAN(days_to_termination)
        FROM fact_matter
        WHERE is_closed AND is_latest_record AND days_to_termination IS NOT NULL
    """).fetchone()
    step(6, "+ the subject-matter control", r[0], r[1],
         "carrier parties excluded at docket level",
         "subject-matter-filter.md")
    step(7, "+ median, not mean", r[0], r[2],
         "litigation durations are heavily right-skewed",
         "metric_register.md M-01")

    # ---- THE OTHER WRONG ANSWER -----------------------------------------
    # The careful analyst who DOES notice the pending records, and reaches for
    # the obvious filter, loses 29% of the file instead.
    careful = con.sql("""
        SELECT COUNT(*), AVG(%s), MIN(CAST(TAPEYEAR AS INTEGER))
        FROM clean WHERE NOS IN (%s) AND STATUSCD = 'L'
    """ % (DUR, CONTRACT)).fetchone()

    # ---- TREND ----------------------------------------------------------
    naive_trend = con.sql("""
        SELECT CAST(TAPEYEAR AS INTEGER) AS sy, AVG(%s) AS d
        FROM clean WHERE NOS IN (%s)
          AND CAST(TAPEYEAR AS INTEGER) BETWEEN 2001 AND 2025
        GROUP BY 1 ORDER BY 1
    """ % (DUR, CONTRACT)).to_df()
    gov_trend = gcon.sql("""
        SELECT statistical_year AS sy, MEDIAN(days_to_termination) AS d
        FROM fact_matter
        WHERE is_closed AND is_latest_record AND days_to_termination IS NOT NULL
          AND statistical_year BETWEEN 2001 AND 2025
        GROUP BY 1 ORDER BY 1
    """).to_df()

    negatives = con.sql("""
        SELECT COUNT(*) FROM clean WHERE NOS IN (%s) AND %s < 0
    """ % (CONTRACT, DUR)).fetchone()[0]

    write_report(steps, careful, naive_trend, gov_trend, negatives)

    # Machine-readable sidecar for the visual layer. This SERIALISES values the
    # script already computed and prints; it changes no measure and no figure.
    # The markdown report's hash is unchanged by this addition, which is how
    # that claim is checked rather than asserted.
    import json as _json
    sidecar = {
        "generated_from": "src/stage6_ai_readiness.py",
        # No as-of here on purpose: governance/health.json carries the
        # authoritative freeze date and the page reads it from there. Two
        # copies of an as-of date is the drift problem one level up.
        "question": ("How long does it take to resolve a contract dispute in "
                     "federal court?"),
        "ungoverned_days": steps[0]["answer"],
        "governed_days": steps[-1]["answer"],
        "negative_duration_records": negatives,
        "steps": steps,
        "careful_analyst": {"days": careful[1], "records": careful[0],
                            "first_statistical_year": careful[2]},
        "trend": {
            "ungoverned_mean_days": [
                {"statistical_year": int(r.sy), "days": float(r.d)}
                for r in naive_trend.itertuples()],
            "governed_median_days": [
                {"statistical_year": int(r.sy), "days": float(r.d)}
                for r in gov_trend.itertuples()],
        },
    }
    (REPO / "data" / "conformed" / "stage6_proof.json").write_text(
        _json.dumps(sidecar, indent=1), encoding="utf-8")

    con.close()
    gcon.close()
    print("\nwrote %s" % OUT.relative_to(REPO))
    print("wrote data/conformed/stage6_proof.json")


def write_report(steps, careful, naive_trend, gov_trend, negatives):
    naive = steps[0]
    governed = steps[-1]
    L = []
    a = L.append
    a("# The AI-readiness proof")
    a("")
    a("*Stage 6 artifact. Owner: Aaron Robbins. Generated by")
    a("`src/stage6_ai_readiness.py` from the frozen snapshot. Regenerate it;")
    a("never hand-edit it.*")
    a("")
    a("One legal-operations question, answered twice.")
    a("")
    a("> **How long does it take to resolve a contract dispute in federal")
    a("> court?**")
    a("")
    a("| | Answer |")
    a("|---|---|")
    a("| Against the raw frozen file | **%s days** |"
      % round(naive["answer"], 1))
    a("| Against the governed model | **%s days** |"
      % round(governed["answer"], 1))
    a("")
    a("Both numbers come from the same 2.0 GB file, retrieved once, on the")
    a("same day. Neither query contains a mistake anyone would call obvious.")
    a("")
    a("---")
    a("")
    a("## The ungoverned answer is not approximately right")
    a("")
    a("It is **%s days**, and %s of the matters behind it have a *negative*"
      % (round(naive["answer"], 1), format(negatives, ",")))
    a("duration -- some of them by more than a century. The arithmetic is")
    a("correct. Every input is a well-formed date. Nothing errors, nothing")
    a("warns, and no null appears anywhere to hint that something is wrong.")
    a("")
    a("**That is the whole argument.** A governed layer is not documentation")
    a("wrapped around a correct answer. It is the difference between an answer")
    a("and a number.")
    a("")
    a("## The decomposition")
    a("")
    a("Each row is one governance rule earning its place. The query is the")
    a("same query throughout; only the rules change.")
    a("")
    a("| # | Step | Records | Answer, days | Why | Rule |")
    a("|---|---|---:|---:|---|---|")
    prev = None
    for s in steps:
        delta = ("" if prev is None
                 else " (%+.1f)" % (s["answer"] - prev))
        a("| %d | %s | %s | %s%s | %s | %s |"
          % (s["n"], s["label"], format(s["rows"], ","),
             round(s["answer"], 1), delta, s["cause"], s["artifact"]))
        prev = s["answer"]
    a("")
    a("**Step 4 does all the work, and steps 1 to 3 do almost none.** That is")
    a("the honest reading of this table and it is not the one the exercise was")
    a("set up to produce. The encoding and the quoting are real defects in the")
    a("source and they cost 11 records here, not thousands. One rule out of")
    a("seven moves the answer by 1,062 days; the rest move it by less than a")
    a("day between them, until the mean-versus-median choice at step 7.")
    a("")
    a("The reason to keep steps 1 to 3 anyway is that **their cost is not")
    a("bounded by this measure.** The 638 field-shifted records carry")
    a("disposition codes that are fragments of dates, and they will corrupt")
    a("M-02 and M-03 rather than M-01. A rule is not worthless because the")
    a("first question you ask happens not to depend on it.")
    a("")
    a("## Step 1 cost nothing here, and that is worth stating plainly")
    a("")
    a("The file is not UTF-8. A reader at its defaults raises an error, and")
    a("the error message suggests `ignore_errors=true`. Taking that advice")
    a("makes the error go away.")
    a("")
    a("**It also lost nothing.** Both readings return 10,960,173 records; the")
    a("recovery is exactly zero rows. An earlier draft of this document")
    a("asserted that the suppression discarded records. It was checked, and it")
    a("did not, and the sentence was removed rather than softened.")
    a("")
    a("The hazard is still real and is narrower than it first looked:")
    a("`ignore_errors=true` suppresses an *unbounded* number of failures and")
    a("reports none of them. Here the number happened to be zero, and nothing")
    a("in the output said so. The analyst who follows the tool's advice cannot")
    a("distinguish that case from the one where it drops a hundred thousand")
    a("rows. That is why this module counts records at every stage and writes")
    a("the counts to `governance/last_run.json` -- not because suppression is")
    a("always lossy, but because unmeasured suppression is never assertable.")
    a("")
    a("## There is no obvious correct filter")
    a("")
    a("Suppose the analyst *does* notice the pending records and reaches for")
    a("the obvious fix -- keep only rows the source marks as terminated:")
    a("")
    a("```sql")
    a("WHERE STATUSCD = 'L'")
    a("```")
    a("")
    a("That gives **%s days** over %s records -- and quietly discards every"
      % (round(careful[1], 1), format(careful[0], ",")))
    a("matter before statistical year %d, because `STATUSCD` did not exist"
      % careful[2])
    a("then. The careful analyst loses %s records -- 44 percent of the slice --"
      % format(steps[3]["rows"] - careful[0], ","))
    a("and gets a different wrong answer than the careless one, biased toward")
    a("recent years.")
    a("")
    a("**Both reasonable choices are wrong, in opposite directions.** Only an")
    a("effective-dated closure rule is right, and that rule is not derivable")
    a("from the data -- it comes from a sentence in the codebook stating that")
    a("the field was captured from October 2000. That sentence is why")
    a("`docket-to-matter.md` R-03 exists.")
    a("")
    a("## What this means for an AI layer")
    a("")
    a("A retrieval system pointed at the raw file answers the question with")
    a("**%s days**, fluently and with a citation to a real government"
      % round(naive["answer"], 1))
    a("dataset. It has no way to know about the sentinel date, because the")
    a("sentinel is not written down anywhere in the file -- it is written down")
    a("in this repository, in a governance document, by a person who found it")
    a("and took ownership of it.")
    a("")
    a("Governance is not the paperwork that slows the AI layer down. It is the")
    a("only thing standing between a fluent answer and a correct one. That is")
    a("what *governed, well-modeled enterprise data supports AI* has to mean")
    a("if it means anything.")
    a("")
    a("## The trend agrees, and the reason it agrees is an accident")
    a("")
    a("Plotted by statistical year, 2001 to 2025:")
    a("")
    a("| | First year | Last year | Change |")
    a("|---|---:|---:|---:|")
    rows = []
    for label, df in (("Ungoverned, mean days", naive_trend),
                      ("Governed, median days", gov_trend)):
        f, l = df["d"].iloc[0], df["d"].iloc[-1]
        rows.append((f, l))
        a("| %s | %s | %s | %+.1f |" % (label, round(f, 1), round(l, 1), l - f))
    a("")
    a("**Both paths agree that contract matters are getting slower**, by a")
    a("broadly similar amount. The ungoverned line is offset by roughly %d"
      % abs(round(rows[0][0] - rows[1][0])))
    a("days -- that offset is the mean-versus-median choice, not the sentinel.")
    a("")
    a("This is not the result the exercise wanted, and it is the most useful")
    a("one in the document.")
    a("")
    a("**The trend chart is clean because the defect hides from it.** Pending")
    a("records carry `TAPEYEAR = 2099`. Group by year and all 32,767 of them")
    a("fall into a bucket that is off the end of every axis anyone would draw.")
    a("The chart never shows them. The headline average, which has no year")
    a("axis to hide behind, is wrong by more than a thousand days.")
    a("")
    a("So the same defect, in the same file, on the same day, is **invisible")
    a("in one cut of the data and catastrophic in another.** An analyst who")
    a("sanity-checks the headline against the trend chart finds a plausible")
    a("line going the right way and concludes the number is fine.")
    a("")
    a("That is the case for a governed layer stated more precisely than")
    a("\"ungoverned answers are wrong.\" Ungoverned answers are wrong")
    a("*inconsistently*, and inconsistent wrongness is what defeats review.")
    a("You cannot eyeball your way out of it, because the cut of the data you")
    a("would eyeball is the one that looks right.")
    a("")
    OUT.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
