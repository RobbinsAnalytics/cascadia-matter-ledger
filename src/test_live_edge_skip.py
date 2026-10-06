"""Drive pull_live_edge.main()'s quota/skip path in a throwaway directory.

No network: Client.usage is replaced with a crafted response, and every skip
returns before the first data request. No repo file is touched: LIVE, CACHE,
STATE and GOV are pointed at a temp dir. Usage: test_skip.py <path-to-source>
"""
import importlib.util
import json
import os
import pathlib
import sys
import tempfile
from datetime import datetime, timedelta, timezone

SRC = (sys.argv[1] if len(sys.argv) > 1 else
       str(pathlib.Path(__file__).resolve().parent / "pull_live_edge.py"))
os.environ["COURTLISTENER_TOKEN"] = "dummy-not-a-real-token"
NOW = datetime.now(timezone.utc)


def usage(day=(0, 125), hour=(0, 50), minute=(5, 5), blocked=(), drop=()):
    """(remaining, limit) per window; `used` is derived."""
    rows = {}
    for rate, (rem, lim) in (("125/day", day), ("50/hour", hour),
                             ("5/min", minute)):
        if rate in drop:
            continue
        rows[rate] = {"scope": "user", "rate": rate, "remaining": rem,
                      "limit": lim, "used": lim - rem,
                      "blocked": rate in blocked, "reset_at": None}
    return rows


def hist(*runs):
    """runs: (minutes_ago, requests_made or None)."""
    out = []
    for mins, n in runs:
        e = {"started_utc": (NOW - timedelta(minutes=mins)).isoformat(
                 timespec="seconds"), "status": "ok"}
        if n is not None:
            e["requests_made"] = n
        out.append(json.dumps(e))
    return "\n".join(out) + ("\n" if out else "")


def run(case_usage, history):
    spec = importlib.util.spec_from_file_location("ple_%d" % id(case_usage), SRC)
    ple = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ple)
    d = pathlib.Path(tempfile.mkdtemp())
    (d / "live" / "cache").mkdir(parents=True)
    (d / "gov").mkdir()
    ple.LIVE, ple.CACHE = d / "live", d / "live" / "cache"
    ple.STATE, ple.GOV = d / "live" / "watermark.json", d / "gov"
    ple.STATE.write_text(json.dumps({"dockets_ingested": [], "runs": 0}))
    (ple.GOV / "run_history.jsonl").write_text(history)
    ple.Client.usage = lambda self: case_usage
    rc = ple.main()
    rec = json.loads((ple.GOV / "last_live_run.json").read_text())
    last_hist = json.loads((ple.GOV / "run_history.jsonl").read_text()
                           .splitlines()[-1])
    failed = [c["check"] for c in rec["checks"] if c.get("passed") is False]
    return rc, rec, failed, last_hist


fails = 0
def case(name, fn):
    global fails
    try:
        fn()
        print("  PASS  %s" % name)
    except AssertionError as e:
        fails += 1
        print("  FAIL  %s\n          %s" % (name, e))
    except Exception as e:  # noqa: BLE001
        fails += 1
        print("  FAIL  %s\n          %s: %s" % (name, type(e).__name__, e))


def own_spend_explains_it():
    # 16:12 today: four runs inside the hour spent the window.
    rc, rec, failed, _ = run(usage(day=(75, 125), hour=(0, 50)),
                             hist((47, 0), (43, 0), (41, 6), (28, 43)))
    assert rec["status"] == "skipped: no quota headroom in the binding window", rec["status"]
    assert not failed, failed
    assert "binding: hour" in rec["notes"][0], rec["notes"]

def day_binds_is_named_day():
    rc, rec, failed, _ = run(usage(day=(20, 125), hour=(40, 50)),
                             hist((300, 55), (600, 50)))
    assert "binding: day" in rec["notes"][0], rec["notes"][0]
    assert "hour" not in rec["notes"][0].split("binding:")[1], rec["notes"][0]

def all_zero_with_no_own_spend_is_flagged():
    # The 09-18 .. 10-01 case: every window zero, this pipeline spent nothing.
    rc, rec, failed, _ = run(usage(day=(0, 125), hour=(0, 50), minute=(0, 5)),
                             hist((700, 0), (1400, 0)))
    assert rec["status"] == "skipped: quota spent elsewhere", rec["status"]
    assert "quota spend attributable to this pipeline" in failed, failed

def blocked_is_flagged():
    rc, rec, failed, _ = run(usage(day=(0, 125), hour=(0, 50), blocked=("50/hour",)),
                             hist())
    assert rec["status"] == "skipped: blocked upstream", rec["status"]
    assert "quota windows blocked upstream" in failed, failed

def missing_window_is_flagged():
    rc, rec, failed, _ = run(usage(drop=("125/day",)), hist())
    assert rec["status"] == "skipped: quota unreadable", rec["status"]
    assert "quota windows present in the response" in failed, failed

def incomplete_history_does_not_accuse():
    # Runs that predate request counting: attribution is a lower bound only.
    rc, rec, failed, _ = run(usage(day=(0, 125), hour=(0, 50)),
                             hist((30, None), (300, None)))
    assert rec["status"] != "skipped: quota spent elsewhere", rec["status"]
    assert "quota spend attributable to this pipeline" not in failed, failed
    assert any("lower bound" in n for n in rec["notes"]), rec["notes"]

def history_keeps_spend_and_quota():
    rc, rec, failed, h = run(usage(day=(75, 125), hour=(0, 50)), hist())
    assert h.get("requests_made") == 0, h
    assert h.get("quota", {}).get("50/hour", {}).get("remaining") == 0, h

print("main() skip path, %s:" % pathlib.Path(SRC).name)
case("own spend explains the skip -> benign skip, window named 'hour'", own_spend_explains_it)
case("day binds -> named 'day', not hard-coded 'hour'", day_binds_is_named_day)
case("all-zero with no own spend (the 09-18 case) -> flagged, not benign", all_zero_with_no_own_spend_is_flagged)
case("blocked upstream -> its own status and a failed check", blocked_is_flagged)
case("window missing from response -> unreadable, not 'spent'", missing_window_is_flagged)
case("history without request counts -> lower bound, no accusation", incomplete_history_does_not_accuse)
case("history line keeps requests_made and the quota snapshot", history_keeps_spend_and_quota)
print("\n%s" % ("ALL PASS" if not fails else "%d FAILED" % fails))
sys.exit(1 if fails else 0)
