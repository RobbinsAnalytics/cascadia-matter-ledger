"""Reconcile the live increment against the frozen baseline, and publish it.

The module is called a Ledger because a ledger balances, and the balancing is
the point. This script compares what the frozen snapshot says exists in the
live edge's slice against what the live edge has actually seen, states the
variance, and attributes it to named causes.

IT DOES NOT TRY TO MAKE THE NUMBERS MATCH. They should not match, and the
reasons they do not are the finding. A reconciliation that always balances is
not being computed.

Writes:
    governance/reconciliation.md    the human record
    governance/health.json          the machine-readable record a frontend
                                    renders: last successful run, rows added,
                                    checks passed, last failure and its cause
"""
import json
import pathlib
import sys
import textwrap
from datetime import datetime, timezone

import duckdb

REPO = pathlib.Path(__file__).resolve().parent.parent
DB = REPO / "data" / "conformed" / "matter_ledger.duckdb"
LIVE = REPO / "data" / "live"
GOV = REPO / "governance"

# cand in IDB terms. Verified against the codebook: 71 = California - Northern,
# circuit 9. The live source calls it 'cand'; the frozen source has never heard
# of that string. Mapping between the two vocabularies is itself a conformance
# step and is stated rather than assumed.
CAND_CIRCUIT, CAND_DISTRICT = "9", "71"
SLICE_NOS = "190"
SLICE_START = "2024-01-01"


def main():
    if not DB.exists():
        sys.exit("Run src/build_conformed.py first.")
    con = duckdb.connect(str(DB), read_only=True)

    frozen = con.sql("""
        SELECT COUNT(DISTINCT matter_key) AS matters,
               MIN(filed_date) AS earliest, MAX(filed_date) AS latest
        FROM fact_matter
        WHERE CIRCUIT = ? AND DISTRICT = ? AND nature_of_suit_code = ?
          AND filed_date >= CAST(? AS DATE)
    """, params=[CAND_CIRCUIT, CAND_DISTRICT, SLICE_NOS, SLICE_START]).fetchone()
    frozen_matters, frozen_earliest, frozen_latest = frozen

    frozen_open = con.sql("""
        SELECT COUNT(*) FROM fact_matter
        WHERE CIRCUIT = ? AND DISTRICT = ? AND nature_of_suit_code = ?
          AND filed_date >= CAST(? AS DATE) AND NOT is_closed AND is_latest_record
    """, params=[CAND_CIRCUIT, CAND_DISTRICT, SLICE_NOS, SLICE_START]).fetchone()[0]
    con.close()

    state = json.loads((LIVE / "watermark.json").read_text(encoding="utf-8"))
    run = json.loads((GOV / "last_live_run.json").read_text(encoding="utf-8"))

    # Make sure the run record on disk is in the history before reading it
    # back. The history was added after several runs had already happened, so
    # without this the current run would be missing from it until the next
    # scheduled pull. Idempotent on started_utc; it back-dates nothing and
    # invents nothing -- it ingests a record that already exists on disk.
    sys.path.insert(0, str(REPO / "src"))
    from pull_live_edge import append_history
    append_history(run)

    history = []
    hpath = GOV / "run_history.jsonl"
    if hpath.exists():
        for line in hpath.read_text(encoding="utf-8").splitlines():
            if line.strip():
                history.append(json.loads(line))
    history.sort(key=lambda r: r.get("started_utc") or "")

    def latest(pred):
        for r in reversed(history):
            if pred(r):
                return r
        return None

    last_ok = latest(lambda r: r.get("status") == "ok")
    # Anything that is not a clean "ok": a rate-limit stop, a skip, or a real
    # failure. They are NOT the same thing and the record keeps them apart.
    last_not_ok = latest(lambda r: r.get("status") != "ok")
    last_failure = latest(lambda r: r.get("status") == "failed"
                          or r.get("checks_failed"))

    rows, dockets_with_rows, events = [], set(), {}
    out = LIVE / "fact_docket_event.jsonl"
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            rows.append(r)
            dockets_with_rows.add(r["docket_id"])
            events[r["docket_event_type"]] = \
                events.get(r["docket_event_type"], 0) + 1

    roster = len(state.get("dockets_known", []))
    partial = len(state.get("partial_dockets", {}))
    complete = len(dockets_with_rows) - partial

    variance = roster - frozen_matters

    health = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "module": "cascadia-matter-ledger",
        "frozen_baseline": {
            "as_of": "2026-08-26",
            "slice_matters": frozen_matters,
            "slice_open_matters": frozen_open,
        },
        "live_edge": {
            "roster_dockets": roster,
            "roster_complete": state.get("roster_complete", False),
            # `roster_complete: false` alone cannot distinguish "still
            # working through it" from "the query that extends it no longer
            # returns", and those are different claims about coverage. The
            # stall counter resets on any roster page that does come back,
            # so a number above 1 means the roster is capped at what is
            # already known rather than merely unfinished.
            "roster_stalls_consecutive": state.get("roster_stalls", 0),
            "roster_last_stall": state.get("roster_last_stall"),
            "dockets_fully_ingested": max(0, complete),
            "dockets_partial": partial,
            "entries_derived": len(rows),
            "event_counts": dict(sorted(events.items(), key=lambda kv: -kv[1])),
            "watermark": state.get("docket_watermark", 0),
            "runs_total": state.get("runs", 0),
        },
        "last_run": {
            "started_utc": run.get("started_utc"),
            "finished_utc": run.get("finished_utc"),
            "status": run.get("status"),
            "passed": run.get("passed"),
            "checks_total": len(run.get("checks", [])),
            "checks_failed": [c["check"] for c in run.get("checks", [])
                              if c.get("passed") is False],
            "error": run.get("error"),
        },
        "run_history": {
            "runs_recorded": len(history),
            "history_started": history[0]["started_utc"] if history else None,
            "last_successful_run": last_ok,
            "last_not_ok_run": last_not_ok,
            "last_failed_run": last_failure,
            "_note": ("The history begins when the log was added, not when the "
                      "module did. Earlier runs were overwritten in place and "
                      "are not recoverable; they are not reconstructed here."),
        },
        "reconciliation": {
            "roster_vs_frozen_variance": variance,
            "balances": False,
            "reason_not_balanced": "expected; see governance/reconciliation.md",
        },
    }
    (GOV / "health.json").write_text(json.dumps(health, indent=1),
                                     encoding="utf-8")

    unclassified = events.get("UNCLASSIFIED", 0)
    pct = round(100.0 * unclassified / len(rows), 1) if rows else 0.0

    L = []
    a = L.append
    a("# Live increment vs frozen baseline")
    a("")
    a("*Generated by `src/reconcile_live_edge.py`. Regenerate it; never")
    a("hand-edit it. Machine-readable form: `governance/health.json`.*")
    a("")
    a("The slice, in both vocabularies: **N.D. Cal.**, contract nature of suit")
    a("**190**, filed on or after **%s**. The live source calls that court" % SLICE_START)
    a("`cand`; the frozen source calls it circuit %s district %s and has never"
      % (CAND_CIRCUIT, CAND_DISTRICT))
    a("heard of the string `cand`. Mapping between them is a conformance step,")
    a("not a lookup, and it is stated here rather than buried in a join.")
    a("")
    a("| | Count |")
    a("|---|---:|")
    a("| Frozen baseline — matters in slice | **%s** |" % format(frozen_matters, ","))
    a("| Frozen baseline — of those, still open | %s |" % format(frozen_open, ","))
    a("| Live edge — dockets on roster | **%s** |" % format(roster, ","))
    a("| Live edge — dockets fully ingested | %s |" % format(max(0, complete), ","))
    a("| Live edge — dockets partially ingested | %s |" % format(partial, ","))
    a("| Live edge — docket entries derived | %s |" % format(len(rows), ","))
    a("")
    a("**Variance, roster against frozen baseline: %+d.**" % variance)
    a("")
    # "yet" was right while the roster could still grow into the gap. Once
    # the roster is complete the remaining variance is structural, and
    # calling it temporary would tell a reader to wait for something that is
    # never going to happen.
    a("## It does not balance, and it is not supposed to"
      if state.get("roster_complete") else
      "## It does not balance, and it is not supposed to yet")
    a("")
    a("A reconciliation that always balances is not being computed. These are")
    a("the reasons this one does not, in order of size:")
    a("")
    # THREE STATES, NOT ONE. This section asserted "the roster is incomplete"
    # unconditionally until 2026-08-29, because completion was unreachable --
    # the enumerating query could not terminate, so the incomplete case was
    # the only case. Making it terminate made this text self-contradictory:
    # it printed "the roster is incomplete: roster_complete is True".
    if state.get("roster_complete"):
        for line in textwrap.wrap(
                "**1 · The roster is complete, and the gap is not a "
                "backlog.** `roster_complete` is `True`. The slice has been "
                "enumerated down to a derived id floor -- see "
                "`live-edge-design.md` W-05 -- so the %s dockets on the "
                "roster are every docket in this slice the source will "
                "return. The variance below is therefore structural rather "
                "than a queue that drains, and it moves only as new cases "
                "are filed." % format(roster, ","), width=72):
            a(line)
        a("")
    else:
        a("**1 · The roster is incomplete.** `roster_complete` is `False`.")
        a("The roster is built a page at a time inside a rate limit and is")
        a("not finished, so the live count is a lower bound. This is the")
        a("dominant term.")
        a("")
    # "It shrinks by itself" was asserted here unconditionally until
    # 2026-08-29, and a stalled roster makes that false: the term stops
    # shrinking entirely, and a reader who takes the variance as
    # self-correcting reads the coverage gap as temporary when it is not.
    if state.get("roster_complete"):
        pass          # a complete roster is neither shrinking nor stalled
    elif state.get("roster_stalls", 0):
        stall = state.get("roster_last_stall") or {}
        n = state["roster_stalls"]
        for line in textwrap.wrap(
                "**It is not currently shrinking.** Roster extension has "
                "failed upstream on %s; the most recent was %s and returned "
                "`%s`. Until that query returns, the roster is capped at the "
                "%s dockets already known, and this variance is a floor "
                "rather than a lower bound that improves. Treat it as a "
                "coverage limit, not as a queue that drains."
                % ("the last run" if n == 1 else "%d consecutive runs" % n,
                   stall.get("utc", "an unrecorded time"),
                   stall.get("detail", "an unrecorded error"),
                   format(roster, ",")),
                width=72):
            a(line)
        a("")
    else:
        a("It rises on every run and this term shrinks by itself.")
        a("")
    a("**2 · The two sources count different things.** The frozen IDB is a")
    a("case-level administrative record of every civil case reported to the")
    a("Administrative Office. RECAP holds what somebody purchased or")
    a("contributed from PACER. Neither is a subset of the other.")
    a("")
    a("**3 · The freeze lags.** The IDB is refreshed quarterly and this")
    a("snapshot was taken 2026-08-26; a case filed last week is in RECAP and")
    a("not in the freeze. The live edge is, by construction, ahead.")
    a("")
    a("**4 · Nature of suit is coded differently.** The frozen source stores a")
    a("three-digit code. The live source stores free text that happens to")
    a("begin with it. `istartswith` bridges them and would not survive a court")
    a("that formats the field differently.")
    a("")
    a("## The derived events")
    a("")
    if events:
        a("| Event type | Entries |")
        a("|---|---:|")
        for k, v in sorted(events.items(), key=lambda kv: -kv[1]):
            a("| `%s` | %s |" % (k, format(v, ",")))
        a("")
        a("**`UNCLASSIFIED` is %s%% and that is a health metric, not a bug.**" % pct)
        a("Most of it is entries with no description text at all — RECAP holds")
        a("the docket line without the document. They are retained and counted")
        a("rather than dropped, because an entry with no text is still evidence")
        a("that something happened, and discarding it would silently shrink")
        a("every denominator. See `docket-event-derivation.md` D-04 and D-05.")
    else:
        a("No events derived yet.")
    a("")
    a("## Last run")
    a("")
    a("| | |")
    a("|---|---|")
    a("| Started | %s |" % run.get("started_utc"))
    a("| Status | **%s** |" % run.get("status"))
    a("| Assertions | %d, %d failed |"
      % (len(run.get("checks", [])),
         len([c for c in run.get("checks", []) if c.get("passed") is False])))
    if run.get("error"):
        a("| Error | `%s` |" % run["error"])
    a("")
    a("A run that stops early because the rate limit bound it is recorded as")
    a("stopped, not as failed, and it says which window bound it. A run that")
    a("fails an assertion is recorded as failed and publishes which one. The")
    a("distinction is deliberate: a pipeline that reports designed")
    a("backpressure as failure trains its reader to ignore red.")
    a("")
    (GOV / "reconciliation.md").write_text("\n".join(L), encoding="utf-8")

    print("frozen slice matters      %s" % format(frozen_matters, ","))
    print("live roster dockets       %s" % format(roster, ","))
    print("live entries derived      %s" % format(len(rows), ","))
    print("variance                  %+d" % variance)
    print("UNCLASSIFIED              %s%%" % pct)
    print("\nwrote governance/reconciliation.md and governance/health.json")


if __name__ == "__main__":
    main()
