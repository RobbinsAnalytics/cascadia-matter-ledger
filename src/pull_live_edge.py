"""The live edge: a watermarked, resumable, rate-limit-aware incremental pull.

Slice: N.D. Cal. (`cand`), nature of suit 190 -- "Contract: Other" -- which is
the largest single code in the frozen model's contract scope. Deliberately one
court: see governance/docket-event-derivation.md D-03.

WHAT THIS SCRIPT GUARANTEES

  Never re-fetches.   Every response is written to data/live/cache/ keyed by
                      its URL and is read from there forever after. A docket
                      already ingested is never requested again.
  Resumable.          Progress is a watermark -- the highest docket id fully
                      ingested. A run killed halfway loses nothing; the next
                      run continues from the watermark.
  Inside the limit.   The remaining quota is read from the API's own usage
                      endpoint, which has an independent throttle and costs
                      nothing to call. The run stops when the reserve is
                      reached, and says so.
  Fails loudly.       Every run writes a record of what it did, which checks
                      it asserted, and what failed. A failed run publishes the
                      failure. It does not retry silently and it does not
                      leave the previous run's record in place.

DESIGN NOTE, RECORDED BECAUSE IT COST TWO PROBES
    The obvious query -- filter docket-entries by the parent docket's court
    AND nature of suit in one request -- TIMES OUT SERVER-SIDE after 150s.
    Filtering entries by `docket=<id>`, a direct foreign key, returns in about
    0.3s. So the pull is two phases: build a roster of dockets in the slice,
    then walk it. That is slower in requests and roughly 500x faster in wall
    clock, and it is the only shape that completes at all.

Reads COURTLISTENER_TOKEN from the environment. Never logs it.
"""
import json
import hashlib
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

REPO = pathlib.Path(__file__).resolve().parent.parent
LIVE = REPO / "data" / "live"
CACHE = LIVE / "cache"
STATE = LIVE / "watermark.json"
GOV = REPO / "governance"

API = "https://www.courtlistener.com/api/rest/v4"
COURT = "cand"
NOS_PREFIX = "190"
SLICE_START = "2024-01-01"

# Leave this many requests unspent so a run never exhausts the daily budget
# and never starves an interactive check.
QUOTA_RESERVE = 25
# Hard ceiling per run regardless of quota, so one run cannot consume the day.
MAX_REQUESTS_PER_RUN = 55
# Minimum seconds between requests. The documented limit is 5/minute, which is
# one every 12 seconds exactly. 12.5s was tried and produced a 429 on the first
# run: the window is ROLLING, so requests made before this process started were
# still inside it. Pacing to the arithmetic limit leaves no room for anything
# that came before. 15s is 4/minute and leaves that room.
MIN_INTERVAL = 15.0
# A 429 is the throttle doing its job, not a defect. Back off once, then stop
# the walk cleanly and let the next run resume from the watermark.
RETRY_AFTER_CAP = 90

USER_AGENT = ("Cascadia Matter Ledger (portfolio analytics; "
              "contact ajayrobbins@hotmail.com)")

# governance/docket-event-derivation.md R-05. Order matters only in that the
# longest form is tried first; every entry is matched at position zero.
VOCABULARY = [
    ("JUDGMENT", ["CLERK'S JUDGMENT", "JUDGMENT"]),
    ("COMPLAINT", ["COMPLAINT"]),
    ("MOTION", ["MOTION"]),
    ("ORDER", ["ORDER"]),
    ("ANSWER", ["ANSWER"]),
    ("NOTICE", ["NOTICE"]),
    ("STIPULATION", ["STIPULATION"]),
    ("DECLARATION", ["DECLARATION"]),
    ("RESPONSE", ["RESPONSE", "REPLY", "OPPOSITION"]),
    ("TRANSCRIPT", ["TRANSCRIPT"]),
    ("SUMMONS", ["SUMMONS"]),
]


def classify(description):
    """R-05. The keyword must appear at POSITION ZERO -- see R-05.a."""
    if not description:
        return "UNCLASSIFIED"
    text = description.lstrip(" \t\r\n*-–—()[]").upper()
    for event_type, keywords in VOCABULARY:
        for kw in keywords:
            if text.startswith(kw):
                return event_type
    return "UNCLASSIFIED"


class RateLimited(Exception):
    """The throttle refused us. Expected backpressure, not a failure."""


class Client:
    def __init__(self, token):
        self._token = token
        self.requests_made = 0
        self.throttle_waits = 0
        self._last = 0.0

    def _raw(self, url, timeout=120, _retried=False):
        req = urllib.request.Request(url, headers={
            "Authorization": "Token %s" % self._token,
            "User-Agent": USER_AGENT,
        })
        gap = MIN_INTERVAL - (time.monotonic() - self._last)
        if gap > 0:
            time.sleep(gap)
        self._last = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code != 429:
                raise
            if _retried:
                raise RateLimited("throttled again after backing off")
            wait = RETRY_AFTER_CAP
            try:
                wait = min(RETRY_AFTER_CAP,
                           max(5, int(exc.headers.get("Retry-After", "60"))))
            except (TypeError, ValueError):
                pass
            self.throttle_waits += 1
            print("  throttled; waiting %ds then retrying once" % wait)
            time.sleep(wait)
            self._last = time.monotonic()
            return self._raw(url, timeout=timeout, _retried=True)

    def usage(self):
        """Free -- the usage endpoint has its own independent throttle."""
        data = self._raw("%s/api-usage/" % API, timeout=45)
        out = {}
        for row in data.get("current_usage", []):
            if row.get("scope") == "user":
                out[row["rate"]] = row
        return out

    def get(self, url, timeout=120):
        """Cached forever. A URL fetched once is never fetched again."""
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]
        path = CACHE / ("%s.json" % key)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8")), True
        data = self._raw(url, timeout=timeout)
        self.requests_made += 1
        path.write_text(json.dumps(data), encoding="utf-8")
        return data, False


def persisted_entry_ids():
    out = LIVE / "fact_docket_event.jsonl"
    seen = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            if line.strip():
                seen.add(json.loads(line)["entry_id"])
    return seen


def persist(rows, seen):
    """Append derived rows, then flush and fsync before returning.

    THE WATERMARK MAY ONLY ADVANCE AFTER THIS RETURNS. The first version of
    this script advanced the watermark inside the walk and wrote the rows once
    at the end. Run 1 walked 36 dockets, advanced the watermark past all of
    them, hit a 429, took the failure path, and wrote NO rows. The watermark
    said those dockets were done. Nothing in the run record said otherwise.
    Only the permanent response cache made it recoverable, and a cache is a
    performance decision, not a durability guarantee.

    Persist first, advance second. See governance/live-edge-design.md W-02.
    """
    out = LIVE / "fact_docket_event.jsonl"
    written = 0
    with out.open("a", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            if r["entry_id"] in seen:
                continue
            fh.write(json.dumps(r) + "\n")
            seen.add(r["entry_id"])
            written += 1
        fh.flush()
        os.fsync(fh.fileno())
    return written


def roster_base():
    """The slice, as a query. Everything that bounds it is added by caller."""
    return ("%s/dockets/?court=%s&nature_of_suit__istartswith=%s"
            "&date_filed__gte=%s" % (API, COURT, NOS_PREFIX, SLICE_START))


def derive_id_floor(client, state):
    """The id below which no docket in this slice can exist. See W-05.

    DERIVED, NOT TYPED. A docket row cannot be created before the case it
    describes is filed, so every docket filed on or after SLICE_START has an
    id above the last id created before SLICE_START. That last id is asked
    for directly -- one request, ordered by descending id, filtered to
    dockets created before the slice opens.

    Measured 2026-08-29 in this court: floor 68,128,452, created
    2023-12-31T13:18. The roster's own minimum is 68,868,936, above it, which
    is the consistency check the floor has to pass.

    WHAT THIS RESTS ON, STATED RATHER THAN ASSUMED. The floor is sound only
    if id order is monotonic with creation order across that boundary. The
    unbounded form of that question times out, so it was asked of the 500,000
    ids immediately below the floor, where a violation would most plausibly
    sit: nothing there is filed inside the slice, and nothing there was
    created after the slice opened. Bands further down are unverified. If the
    source ever backfills a docket with an out-of-order id, this floor could
    hide it -- which is why the floor is recorded in state with the date it
    was derived rather than being silently recomputed.

    Cached in state: SLICE_START is frozen, so the floor is too.
    """
    if state.get("roster_id_floor"):
        return state["roster_id_floor"]
    data, _ = client.get("%s/dockets/?court=%s&date_created__lt=%s&order_by=-id"
                         % (API, COURT, SLICE_START))
    results = data.get("results", [])
    # No result means nothing predates the slice in this court, so there is
    # nothing to exclude and zero is the honest floor.
    floor = results[0]["id"] if results else 0
    state["roster_id_floor"] = floor
    state["roster_id_floor_derived_utc"] = \
        datetime.now(timezone.utc).isoformat(timespec="seconds")
    return floor


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"roster_cursor": None, "roster_complete": False,
            "docket_watermark": 0, "dockets_known": [], "runs": 0}


def main():
    token = os.environ.get("COURTLISTENER_TOKEN", "").strip()
    if not token:
        sys.exit("COURTLISTENER_TOKEN is not set in this process's environment.")
    CACHE.mkdir(parents=True, exist_ok=True)

    run = {"started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "slice": {"court": COURT, "nature_of_suit_prefix": NOS_PREFIX,
                     "date_filed_gte": SLICE_START},
           "checks": [], "status": "running"}
    state = load_state()
    client = Client(token)

    def check(name, value, expectation=None, passed=None):
        run["checks"].append({"check": name, "value": value,
                              "expectation": expectation, "passed": passed})
        flag = "" if passed is None else ("  PASS" if passed else "  ** FAIL **")
        print("%-46s %s%s" % (name, value, flag))

    try:
        # ALL THREE WINDOWS APPLY CONCURRENTLY and the most restrictive one
        # controls. The first version budgeted from the daily figure alone,
        # computed a budget of 50 while the hourly window was already at
        # 50/50, and spent the run absorbing 90-second backoffs to make
        # requests that could not succeed. Reading only the limit you happen
        # to remember is not being rate-limit-aware.
        usage = client.usage()
        day_left = usage.get("125/day", {}).get("remaining", 0)
        hour_left = usage.get("50/hour", {}).get("remaining", 0)
        minute_left = usage.get("5/min", {}).get("remaining", 0)
        check("quota remaining - day", day_left)
        check("quota remaining - hour", hour_left)
        check("quota remaining - minute", minute_left)
        budget = max(0, min(MAX_REQUESTS_PER_RUN,
                            day_left - QUOTA_RESERVE,
                            hour_left))
        check("request budget for this run", budget)
        if budget <= 0:
            # Not a failure. The pipeline is designed to make bounded progress
            # and this run has no room to make any. It says so and exits clean.
            run["status"] = "skipped: no quota headroom in the binding window"
            run["notes"] = ["day=%d hour=%d minute=%d; the hour window binds"
                            % (day_left, hour_left, minute_left)]
            finish(run, state, 0, 0, {})
            return 0

        # ---- PHASE A: extend the docket roster --------------------------
        roster = list(state["dockets_known"])
        roster_before = len(roster)
        floor = derive_id_floor(client, state)
        check("roster id floor (derived)", floor)
        url = state["roster_cursor"] or (roster_base() + "&id__gte=%d" % floor)
        # A cursor stored before the floor existed does not carry the bound,
        # and an unbounded cursor is exactly what could not finish. Bound it
        # in place rather than discarding the position already paid for.
        if "id__gte=" not in url:
            url += "&id__gte=%d" % floor
        roster_pages = 0
        throttled = False
        throttled_roster = False
        # A ROSTER FAILURE IS NOT A RUN FAILURE, and it took three dead runs
        # to establish that. Cursor pagination over
        # nature_of_suit__istartswith=190 dies server-side the deeper it
        # goes: measured 2026-08-29, page one returns in 7.2s and the stored
        # resume cursor returns HTTP 504 after 180.3s, while the walk's own
        # docket-entries query answers in 1.7s. The 120s client timeout fires
        # first, so it surfaces as "read operation timed out" rather than as
        # a status code -- the 502 recorded on 2026-08-29T02:23 is this same
        # query failing a different way.
        #
        # Phase A runs before phase B, so letting that reach the outer
        # handler ended the run with 262 already-known dockets unwalked and
        # nothing accomplished. It is treated here the way RateLimited two
        # lines up is already treated: stop extending the roster, keep the
        # cursor, and go do the work that is reachable. What must NOT happen
        # is that this becomes quiet -- an incomplete roster understates
        # coverage against the frozen baseline, so it is checked, noted, and
        # counted across runs below.
        roster_stalled = None
        while (not state["roster_complete"] and client.requests_made < budget
               and roster_pages < 4):
            try:
                data, _ = client.get(url)
            except RateLimited:
                throttled_roster = True
                break
            except (urllib.error.HTTPError, urllib.error.URLError,
                    OSError) as exc:
                roster_stalled = str(getattr(exc, "code", None) or exc)
                break
            for d in data.get("results", []):
                if d["id"] not in roster:
                    roster.append(d["id"])
            roster_pages += 1
            if data.get("next"):
                url = data["next"]
                state["roster_cursor"] = url
            else:
                state["roster_complete"] = True
                state["roster_cursor"] = None
                break

        # ---- PHASE A2: dockets created since the roster was built --------
        # `roster_complete` is TERMINAL: the loop above is skipped forever
        # once it is set. That was harmless only because the descent could
        # never actually finish -- with the floor in place it can, and on the
        # run after it does, discovery would stop dead and the live edge
        # would quietly stop being live. Nothing would error.
        #
        # So the top of the range is swept every run, bounded below by the
        # highest id already known. That is the cheap direction: an id-bounded
        # query measured 4.3s where an unbounded month window took 103s.
        topup_added = 0
        topup_pages = 0
        turl = (roster_base() + "&id__gt=%d&order_by=id" % max(roster)
                if roster else None)
        while (turl and roster_stalled is None
               and client.requests_made < budget and topup_pages < 2):
            try:
                data, _ = client.get(turl)
            except RateLimited:
                throttled_roster = True
                break
            except (urllib.error.HTTPError, urllib.error.URLError,
                    OSError) as exc:
                roster_stalled = str(getattr(exc, "code", None) or exc)
                break
            for d in data.get("results", []):
                if d["id"] not in roster:
                    roster.append(d["id"])
                    topup_added += 1
            topup_pages += 1
            turl = data.get("next")
        check("roster top-up, newly created dockets", topup_added)

        # Consecutive stalls are the number that matters. One is upstream
        # having a bad minute; several in a row means the roster cannot be
        # completed by this query shape and the slice is capped at whatever
        # is already known -- which is a claim about coverage, not a
        # transient. Reset on any page that does come back.
        if roster_stalled:
            state["roster_stalls"] = state.get("roster_stalls", 0) + 1
            state["roster_last_stall"] = {
                "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "detail": roster_stalled,
                "cursor": url,
            }
        elif roster_pages:
            state["roster_stalls"] = 0
        state["dockets_known"] = roster
        check("dockets in roster", len(roster))
        check("  added this run", len(roster) - roster_before)
        check("roster extension stalled upstream", roster_stalled or False)
        if roster_stalled:
            check("  consecutive roster stalls", state["roster_stalls"])
            run.setdefault("notes", []).append(
                "roster extension stalled upstream (%s) at the stored cursor; "
                "the cursor is preserved and the walk continued on dockets "
                "already known. The roster is NOT complete and coverage "
                "against the frozen baseline is understated by whatever this "
                "query has not yet returned." % roster_stalled)

        # ---- PHASE B: walk the roster past the watermark ----------------
        # Ascending docket id. The watermark is the highest id fully ingested,
        # so a run killed mid-walk resumes exactly where it stopped.
        partial = dict(state.get("partial_dockets", {}))
        # Partial dockets are revisited regardless of the watermark. The
        # watermark says "nothing below here is UNSEEN"; it does not say
        # "everything below here is COMPLETE". Those are different claims and
        # conflating them is how coverage gets overstated.
        worklist = [int(k) for k in partial]
        worklist += sorted(i for i in roster
                           if i > state["docket_watermark"] and str(i) not in partial)
        seen = persisted_entry_ids()
        entries, event_counts = [], {}
        dockets_done = 0
        rows_written = 0
        for docket_id in worklist:
            if client.requests_made >= budget or throttled:
                break
            start_url = partial.get(str(docket_id)) or (
                "%s/docket-entries/?docket=%d" % (API, docket_id))
            try:
                data, cached = client.get(start_url)
            except RateLimited:
                throttled = True
                break
            # W-03. A docket is DONE only when its entry list is exhausted.
            # 29 of the first 36 dockets have more than one page, and the
            # first version took page one and advanced the watermark past
            # them -- claiming complete coverage of dockets it had 20 entries
            # of. Page through to the end, or record the docket as partial
            # with its resume cursor and never call it done.
            complete = False
            while True:
                page = data.get("results", [])
                batch = []
                for e in page:
                    et = classify(e.get("description"))
                    event_counts[et] = event_counts.get(et, 0) + 1
                    batch.append({
                        "entry_id": e["id"], "docket_id": docket_id,
                        "date_filed": e.get("date_filed"),
                        "entry_number": e.get("entry_number"),
                        "docket_event_type": et,
                        "description_length": len(e.get("description") or ""),
                    })
                # Persist, THEN advance. Never the other way round -- W-02.
                rows_written += persist(batch, seen)
                entries.extend(batch)
                nxt = data.get("next")
                if not nxt:
                    complete = True
                    break
                if client.requests_made >= budget:
                    partial[str(docket_id)] = nxt
                    break
                try:
                    data, _ = client.get(nxt)
                except RateLimited:
                    throttled = True
                    partial[str(docket_id)] = nxt
                    break
            if complete:
                partial.pop(str(docket_id), None)
                dockets_done += 1
                state["docket_watermark"] = max(state["docket_watermark"],
                                                docket_id)

        check("requests spent", client.requests_made)
        check("throttle waits absorbed", client.throttle_waits)
        if throttled:
            # Not a failed assertion. The throttle is a documented constraint
            # the pipeline is designed around, and stopping cleanly at it is
            # the designed behaviour. It IS recorded, because a run that
            # stopped early and does not say so is lying about its coverage.
            run.setdefault("notes", []).append(
                "stopped early: rate limited. Watermark preserved; the next "
                "run resumes from it. No records lost.")
        check("roster extension throttled", throttled_roster)
        check("walk stopped early on rate limit", throttled)
        check("dockets COMPLETED this run", dockets_done)
        check("dockets still partial", len(partial))
        check("entries derived this run", len(entries))
        check("docket watermark (nothing below is unseen)",
              state["docket_watermark"])
        check("rows persisted this run", rows_written)
        state["partial_dockets"] = partial

        # ---- EV assertions, governance/docket-event-derivation.md -------
        typed = sum(1 for e in entries if e["docket_event_type"])
        check("EV-1 every entry has exactly one event type", typed,
              len(entries), typed == len(entries))

        # EV-2: no entry classified by a keyword found after position zero.
        # Re-derived independently here rather than trusting classify().
        violations = 0
        for e in entries:
            if e["docket_event_type"] == "UNCLASSIFIED":
                continue
            if e["description_length"] == 0:
                violations += 1
        check("EV-2 no classification without leading text", violations, 0,
              violations == 0)

        empty = sum(1 for e in entries if e["description_length"] == 0)
        unclassified = event_counts.get("UNCLASSIFIED", 0)
        rate = (round(100.0 * unclassified / len(entries), 2) if entries else 0)
        check("EV-3 UNCLASSIFIED rate percent", rate)
        check("EV-4 empty descriptions retained", empty, empty, True)

        run["event_counts"] = dict(sorted(event_counts.items(),
                                          key=lambda kv: -kv[1]))
        if roster_stalled and not dockets_done and not rows_written:
            # The roster would not extend AND there was nothing left to walk,
            # so this run achieved nothing. Reporting "ok" because the
            # failure was handled would be a run claiming success for having
            # survived. Handling a failure is not the same as doing work.
            check("run made progress", False, True, False)
            run["error"] = ("roster stalled upstream (%s) and no walk work "
                            "remained" % roster_stalled)
            run["status"] = "failed"
        elif throttled:
            run["status"] = "stopped: rate limited"
        else:
            run["status"] = "ok"
        finish(run, state, dockets_done, len(entries), event_counts)
        return 0

    except RateLimited as exc:
        run["status"] = "stopped: rate limited"
        run["notes"] = ["throttled before any work; nothing lost"]
        check("stopped early on rate limit", True)
        finish(run, state, 0, 0, {})
        return 0

    except (urllib.error.HTTPError, urllib.error.URLError, OSError) as exc:
        detail = getattr(exc, "code", None) or str(exc)
        run["status"] = "failed"
        run["error"] = str(detail)
        check("run completed without error", False, True, False)
        finish(run, state, 0, 0, {})
        print("\nRUN FAILED: %s" % detail)
        return 1


def append_history(run):
    """Append one line per run to governance/run_history.jsonl.

    WHY THIS EXISTS. `last_live_run.json` holds only the most recent run, so
    "when did this last succeed" and "when did it last not" were both
    unanswerable -- the previous run's record is overwritten before anyone
    reads it. That is how the module's one genuine HTTP 429 failure became
    unrecoverable: it was overwritten before it was ever committed, and it
    cannot now be shown without fabricating it, which is not on the table.

    Append-only, one JSON object per line, idempotent on started_utc so a
    re-run or a reconcile pass cannot double-count a run.
    """
    path = GOV / "run_history.jsonl"
    entry = {
        "started_utc": run.get("started_utc"),
        "finished_utc": run.get("finished_utc"),
        "status": run.get("status"),
        "passed": run.get("passed"),
        "checks_total": len(run.get("checks", [])),
        "checks_failed": [c["check"] for c in run.get("checks", [])
                          if c.get("passed") is False],
        "error": run.get("error"),
    }
    for c in run.get("checks", []):
        if c["check"] == "dockets COMPLETED this run":
            entry["dockets_completed"] = c["value"]
        elif c["check"] == "rows persisted this run":
            entry["rows_persisted"] = c["value"]
        elif c["check"] == "entries derived this run":
            entry["entries_derived"] = c["value"]

    seen = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                seen.add(json.loads(line).get("started_utc"))
    if entry["started_utc"] in seen:
        return False
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(entry) + "\n")
    return True


def finish(run, state, dockets, entries, event_counts):
    run["finished_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    run["passed"] = all(c["passed"] for c in run["checks"]
                        if c["passed"] is not None)
    state["runs"] = state.get("runs", 0) + 1
    STATE.write_text(json.dumps(state, indent=1), encoding="utf-8")
    (GOV / "last_live_run.json").write_text(json.dumps(run, indent=1),
                                            encoding="utf-8")
    append_history(run)
    # Rows are NOT written here. They are persisted inside the walk, before
    # the watermark advances past the docket they came from. See W-02.
    print("\nRUN %s (%s)" % ("PASSED" if run["passed"] else "FAILED",
                             run["status"]))


if __name__ == "__main__":
    sys.exit(main())
