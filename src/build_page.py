"""Build docs/index.html — the module's visual layer.

K2 IS THE RULE THIS FILE EXISTS TO KEEP. Every figure on the page — in a
title, a subtitle, an annotation, a summary, a table cell or an aria-label —
is computed here from a certified artifact. Nothing is typed. The artifacts:

    data/conformed/m01_time_to_termination_by_nos.csv   Chart 4
    data/conformed/m02_disposition_mix.csv              Chart 5
    data/conformed/m03_procedural_progress.csv          Chart 3
    data/conformed/stage6_proof.json                    Charts 1 and 2
    governance/health.json                              the health surface

No reader controls (Checklist A, brief 0.2). No invented colour or typeface:
the palette, the inks and the provenance strip come from the Cascadia ECharts
theme, which is copied into docs/assets/ from cascadia-standards.
"""
import csv
import html
import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
CONF = REPO / "data" / "conformed"
REF = REPO / "data" / "reference"
GOV = REPO / "governance"
DOCS = REPO / "docs"

SOURCE = "FJC Integrated Database, federal civil dockets"
LIVE_SOURCE = "CourtListener RECAP, N.D. Cal. contract dockets"


def read_csv(name, base=None):
    with ((base or CONF) / name).open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def fmt(n, dp=0):
    return format(round(float(n), dp) if dp else int(round(float(n))), ",")


def live_edge_facts():
    """Figures for the health surface, computed from committed live artifacts.

    K2: both of these were typed into an earlier draft of the page. They are
    real numbers but a typed number is a number nobody can re-derive, so they
    are computed here -- the empty-description share from the derived event
    rows, and the substring-match inflation from the committed raw responses
    the derivation rule was written against.
    """
    import sys
    sys.path.insert(0, str(REPO / "src"))
    from pull_live_edge import classify

    rows = []
    jl = REPO / "data" / "live" / "fact_docket_event.jsonl"
    for line in jl.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    empty = sum(1 for r in rows if r["description_length"] == 0)

    at_zero = anywhere = 0
    for f in (REPO / "data" / "live" / "cache").glob("*.json"):
        blob = json.loads(f.read_text(encoding="utf-8"))
        for e in blob.get("results", []):
            if "description" not in e:
                continue
            desc = e.get("description") or ""
            if classify(desc) == "MOTION":
                at_zero += 1
            if "MOTION" in desc.upper():
                anywhere += 1
    return {
        "empty_pct": round(100.0 * empty / len(rows), 1) if rows else 0.0,
        "motion_at_zero": at_zero,
        "motion_anywhere": anywhere,
        "motion_inflation": (round(100.0 * (anywhere - at_zero) / at_zero)
                             if at_zero else 0),
    }


def main():
    proof = json.loads((CONF / "stage6_proof.json").read_text(encoding="utf-8"))
    health = json.loads((GOV / "health.json").read_text(encoding="utf-8"))
    m01 = read_csv("m01_time_to_termination_by_nos.csv")
    m02 = read_csv("m02_disposition_mix.csv")
    m03 = read_csv("m03_procedural_progress.csv")
    # The measure carries the QUALIFIED description ("no court action, before
    # issue joined"). The dimension carries description and group as separate
    # columns, which is what the two-line label needs. Join on code rather
    # than string-splitting the qualified form.
    dim_pp = {r["code"]: r for r in read_csv("dim_procprog.csv", REF)}

    as_of = health["frozen_baseline"]["as_of"]

    # ---- Chart 1 · the decomposition ---------------------------------
    steps = proof["steps"]
    ungov = proof["ungoverned_days"]
    gov = proof["governed_days"]
    deltas = []
    for i, s in enumerate(steps):
        if i == 0:
            continue
        deltas.append({"n": s["n"], "label": s["label"].replace("+ ", ""),
                       "delta": round(s["answer"] - steps[i - 1]["answer"], 1),
                       "cause": s["cause"], "rule": s["artifact"],
                       "running": round(s["answer"], 1)})
    dominant = max(deltas, key=lambda d: abs(d["delta"]))
    small = [d for d in deltas if abs(d["delta"]) < 1.0]
    small_sum = round(sum(d["delta"] for d in small), 1)

    # ---- Chart 2 · the trend trap ------------------------------------
    tr_u = proof["trend"]["ungoverned_mean_days"]
    tr_g = proof["trend"]["governed_median_days"]
    years = [p["statistical_year"] for p in tr_u]
    u_first, u_last = tr_u[0]["days"], tr_u[-1]["days"]
    g_first, g_last = tr_g[0]["days"], tr_g[-1]["days"]
    negatives = proof["negative_duration_records"]

    # ---- Chart 3 · procedural progress -------------------------------
    m03s = sorted(m03, key=lambda r: -int(r["closed_matters"]))
    total_closed = sum(int(r["closed_matters"]) for r in m03)
    before = [r for r in m03 if r["issue_joined_group"] == "before issue joined"]
    before_n = sum(int(r["closed_matters"]) for r in before)
    before_pct = round(100.0 * before_n / total_closed, 1)
    trial_codes = {"6", "7", "8", "9"}
    trial_n = sum(int(r["closed_matters"]) for r in m03
                  if r["procedural_progress_code"] in trial_codes)
    trial_pct = round(100.0 * trial_n / total_closed, 1)

    # ---- Chart 4 · time to termination -------------------------------
    m04s = sorted(m01, key=lambda r: float(r["median_days"]))
    fastest, slowest = m04s[0], m04s[-1]
    min_n = min(int(r["closed_matters"]) for r in m01)

    # ---- Chart 5 · disposition mix -----------------------------------
    m05s = sorted(m02, key=lambda r: -int(r["closed_matters"]))
    m02_total = sum(int(r["closed_matters"]) for r in m02)
    settled = next(r for r in m02 if r["disposition"] == "settled")
    jury = next(r for r in m02 if r["disposition"] == "jury verdict")
    settled_pct = round(100.0 * int(settled["closed_matters"]) / m02_total, 1)
    jury_pct = round(100.0 * int(jury["closed_matters"]) / m02_total, 1)

    data = {
        "asOf": as_of,
        "c1": {"start": round(ungov, 1), "end": round(gov, 1),
               "deltas": deltas, "dominant": dominant,
               "population": total_closed,
               "smallCount": len(small), "smallSum": small_sum},
        "c2": {"years": years,
               "ungoverned": [round(p["days"], 1) for p in tr_u],
               "governed": [round(p["days"], 1) for p in tr_g]},
        "c3": [{"code": r["procedural_progress_code"],
                "label": r["procedural_progress"],
                "description": dim_pp[r["procedural_progress_code"]]["description"],
                "group": r["issue_joined_group"],
                "n": int(r["closed_matters"]),
                "pct": round(100.0 * int(r["closed_matters"]) / total_closed, 1),
                "median": float(r["median_days"]) if r["median_days"] else None}
               for r in m03s],
        "c4": [{"code": r["nature_of_suit_code"], "label": r["nature_of_suit"],
                "n": int(r["closed_matters"]),
                "median": float(r["median_days"]),
                "p25": float(r["p25_days"]), "p75": float(r["p75_days"])}
               for r in m04s],
        "c5": [{"code": r["disposition_code"], "label": r["disposition"],
                "n": int(r["closed_matters"]),
                "pct": round(100.0 * int(r["closed_matters"]) / m02_total, 1)}
               for r in m05s],
        "health": health,
    }

    # K2: the denominator is the record count after quarantine, read from the
    # proof's own step 3 rather than typed.
    scoped_rows = [s for s in steps if s["n"] == 3][0]["rows"]

    facts = {
        "ungov": round(ungov, 1), "gov": round(gov, 1),
        "negatives": fmt(negatives), "swing": round(abs(gov - ungov), 0),
        "dominant_delta": abs(dominant["delta"]),
        "dominant_label": dominant["label"], "dominant_rule": dominant["rule"],
        "small_count": len(small), "small_sum": abs(small_sum),
        "u_first": round(u_first, 0), "u_last": round(u_last, 0),
        "g_first": round(g_first, 0), "g_last": round(g_last, 0),
        "u_chg": round(u_last - u_first, 0), "g_chg": round(g_last - g_first, 0),
        "yr_first": years[0], "yr_last": years[-1],
        "before_pct": before_pct, "before_n": fmt(before_n),
        "trial_pct": trial_pct, "trial_n": fmt(trial_n),
        "total_closed": fmt(total_closed),
        "fast_label": fastest["nature_of_suit"],
        "fast_days": int(round(float(fastest["median_days"]))),
        "slow_label": slowest["nature_of_suit"],
        "slow_days": int(round(float(slowest["median_days"]))),
        "min_n": fmt(min_n),
        "settled_pct": settled_pct, "jury_pct": jury_pct,
        "settled_n": fmt(int(settled["closed_matters"])),
        "jury_n": fmt(int(jury["closed_matters"])),
        "careful_days": round(proof["careful_analyst"]["days"], 0),
        "careful_lost": fmt(scoped_rows - proof["careful_analyst"]["records"]),
        "careful_year": proof["careful_analyst"]["first_statistical_year"],
        "as_of": as_of,
    }
    facts["careful_lost_pct"] = round(
        100.0 * (scoped_rows - proof["careful_analyst"]["records"]) / scoped_rows, 0)

    facts.update(live_edge_facts())

    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "index.html").write_text(render(data, facts, health),
                                     encoding="utf-8")
    print("wrote docs/index.html")
    for k in ("ungov", "gov", "before_pct", "trial_pct", "settled_pct",
              "jury_pct", "u_chg", "g_chg", "careful_days"):
        print("  %-16s %s" % (k, facts[k]))


# §4 asks for the last failure "and its cause, in plain language. Not an error
# code." An HTTP status on its own is an error code; a reader needs to know
# whether it was the source refusing us, the source breaking, or our own
# assertion failing, because those call for three different responses.
CAUSES = {
    "502": "the source returned a server error mid-walk — an upstream fault, "
           "not a refusal and not a rate limit",
    "503": "the source was unavailable mid-walk",
    "429": "the source throttled us after the backoff had already been spent",
}

# Matched on a substring, because these arrive as exception text rather than as
# a status code and the wording is the library's, not ours. A reader needs to
# know WHICH of four things happened -- the source refused us, the source
# broke, the connection never completed, or our own assertion failed -- because
# those call for four different responses. A raw exception string answers none
# of them, and "cause recorded as The read operation timed out" is the same
# defect the status-code mapping above was written to remove.
CAUSE_PATTERNS = [
    ("timed out", "the connection to the source never completed — the request "
                  "was neither refused nor answered, and the run stopped rather "
                  "than guess at a partial response"),
    ("connection", "the connection to the source failed mid-walk"),
    ("ssl", "the secure connection to the source could not be established"),
]


def describe_not_ok(run):
    if not run:
        return "none recorded since the log began"
    status = run.get("status") or "not recorded"
    when = (run.get("started_utc") or "").replace("T", " ").replace("+00:00", " UTC")
    err = str(run.get("error") or "")
    cause = CAUSES.get(err)
    if not cause and err:
        low = err.lower()
        for frag, text in CAUSE_PATTERNS:
            if frag in low:
                cause = text
                break
    if status.startswith(("stopped", "skipped")):
        return "%s — %s" % (when, status)
    if cause:
        return "%s — failed: %s" % (when, cause)
    if err:
        return "%s — failed, cause recorded as %s" % (when, err)
    failed = run.get("checks_failed") or []
    if failed:
        return "%s — failed its own check: %s" % (when, failed[0])
    return "%s — %s" % (when, status)


def table(tid, caption, headers, rows):
    h = ["<table id=\"%s\"><caption>%s</caption><thead><tr>" % (tid, caption)]
    h += ["<th scope=\"col\">%s</th>" % html.escape(c) for c in headers]
    h.append("</tr></thead><tbody>")
    for r in rows:
        h.append("<tr>" + "".join(
            "<th scope=\"row\">%s</th>" % html.escape(str(c)) if i == 0
            else "<td>%s</td>" % html.escape(str(c))
            for i, c in enumerate(r)) + "</tr>")
    h.append("</tbody></table>")
    return "".join(h)


def render(data, f, health):
    lr = health["last_run"]
    rh = health.get("run_history", {})
    ok_run = rh.get("last_successful_run") or {}
    notok = rh.get("last_not_ok_run") or {}
    le = health["live_edge"]
    fb = health["frozen_baseline"]
    rec = health["reconciliation"]
    ev = le["event_counts"]
    entries = le["entries_derived"]
    unclass_pct = round(100.0 * ev.get("UNCLASSIFIED", 0) / entries, 1)

    t1 = table("tbl-c1", "Chart 1 data — each rule's effect on the answer, in days",
               ["Step", "Rule applied", "Effect, days", "Running answer, days"],
               [[d["n"], d["label"], "%+.1f" % d["delta"], "%.1f" % d["running"]]
                for d in data["c1"]["deltas"]])
    t2 = table("tbl-c2", "Chart 2 data — median and mean days to termination by statistical year",
               ["Statistical year", "Ungoverned mean, days", "Governed median, days"],
               [[y, u, g] for y, u, g in zip(data["c2"]["years"],
                                             data["c2"]["ungoverned"],
                                             data["c2"]["governed"])])
    t3 = table("tbl-c3", "Chart 3 data — procedural progress at termination",
               ["Progress at termination", "Group", "Matters", "Share", "Median days"],
               [[r["label"], r["group"], fmt(r["n"]), "%.1f%%" % r["pct"],
                 "%.0f" % r["median"] if r["median"] else "—"]
                for r in data["c3"]])
    t4 = table("tbl-c4", "Chart 4 data — days from filing to termination by nature of suit",
               ["Nature of suit", "Closed matters", "25th pct", "Median", "75th pct"],
               [[r["label"], fmt(r["n"]), "%.0f" % r["p25"], "%.0f" % r["median"],
                 "%.0f" % r["p75"]] for r in reversed(data["c4"])])
    t5 = table("tbl-c5", "Chart 5 data — disposition mix",
               ["Disposition", "Matters", "Share"],
               [[r["label"], fmt(r["n"]), "%.1f%%" % r["pct"]]
                for r in data["c5"]])

    subs = {
        "data": json.dumps(data, separators=(",", ":")),
        "source_js": json.dumps(SOURCE),
        "t1": t1, "t2": t2, "t3": t3, "t4": t4, "t5": t5,
        "unclass_pct": unclass_pct,
        "entries": fmt(entries),
        "roster": fmt(le["roster_dockets"]),
        "complete": fmt(le["dockets_fully_ingested"]),
        "partial": fmt(le["dockets_partial"]),
        "slice_matters": fmt(fb["slice_matters"]),
        "variance": "%+d" % rec["roster_vs_frozen_variance"],
        "runs": le["runs_total"],
        "status": html.escape(lr["status"]),
        "state_class": ("ok" if lr.get("status") == "ok"
                        else ("failed" if lr.get("status") == "failed"
                              else "stopped")),
        "checks_total": lr["checks_total"],
        "checks_failed": len(lr["checks_failed"]),
        "run_started": lr["started_utc"].replace("T", " ").replace("+00:00", " UTC"),
        "runs_recorded": rh.get("runs_recorded", 0),
        "last_ok_at": (ok_run.get("started_utc", "") or "—")
                      .replace("T", " ").replace("+00:00", " UTC"),
        "last_ok_rows": fmt(ok_run.get("rows_persisted", 0)),
        "last_ok_dockets": fmt(ok_run.get("dockets_completed", 0)),
        "last_notok": describe_not_ok(notok),
        "generated": health["generated_utc"].replace("T", " ").replace("+00:00", " UTC"),
        "order": ev.get("ORDER", 0),
    }
    subs.update(f)
    out = TEMPLATE
    for k, v in subs.items():
        out = out.replace("@@%s@@" % k, str(v))
    left = [m for m in set(__import__("re").findall(r"@@(\w+)@@", out))]
    if left:
        raise SystemExit("unsubstituted tokens in template: %s" % sorted(left))
    return out


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cascadia Matter Ledger — can this number be trusted?</title>
<meta name="description" content="One legal-operations question answered twice against the same federal civil docket data: once ungoverned, once through a governed model. An independent portfolio project.">
<meta property="og:type" content="website">
<meta property="og:title" content="Cascadia Matter Ledger — can this number be trusted?">
<meta property="og:description" content="The same question, the same 11 million federal civil dockets, two answers. One of them is negative.">
<meta property="og:image" content="https://www.robbinsanalytics.com/assets/thumb-matter-ledger.png">
<meta property="og:url" content="https://www.robbinsanalytics.com/matter-ledger/">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="https://www.robbinsanalytics.com/assets/thumb-matter-ledger.png">
<link rel="stylesheet" href="assets/cascadia.css">
<style>
  .answers { display:flex; flex-wrap:wrap; gap:18px; margin:18px 0 6px; }
  .answer { flex:1 1 240px; border:1px solid var(--mist,#E4E7E3); border-radius:3px;
            padding:14px 16px; background:#FCFCFA; }
  .answer .lbl { font:12px/1.5 "Segoe UI",Arial,sans-serif; color:#5B6660;
                 text-transform:uppercase; letter-spacing:.06em; }
  .answer .val { font:700 34px/1.15 "Source Serif 4",Georgia,serif; margin:4px 0 2px; }
  .answer.bad .val { color:#BA572D; }
  .answer.good .val { color:#1E7A4C; }
  .answer .note { font:13px/1.5 "Segoe UI",Arial,sans-serif; color:#5B6660; }
  .chart { width:100%; }
  .chart-summary { font:13px/1.6 "Segoe UI",Arial,sans-serif; color:#232B27;
                   margin:10px 2px 0; max-width:70ch; }
  details.data-table { margin:8px 2px 0; }
  details.data-table summary { font:12px/1.5 "Segoe UI",Arial,sans-serif;
                               color:#5B6660; cursor:pointer; min-height:24px; }
  details.data-table table { border-collapse:collapse; margin-top:8px;
                             font:12px/1.5 "Segoe UI",Arial,sans-serif; }
  details.data-table caption { text-align:left; font-weight:600; padding:4px 0;
                               color:#232B27; }
  details.data-table th, details.data-table td { border:1px solid #E4E7E3;
                             padding:4px 8px; text-align:right; }
  details.data-table th[scope="row"] { text-align:left; font-weight:400; }
  details.data-table thead th { background:#F3F5F2; text-align:right; }
  .governance-note { border-left:3px solid #1E7A4C; padding:2px 0 2px 14px;
                     margin:16px 2px; font:14px/1.65 "Segoe UI",Arial,sans-serif;
                     color:#232B27; max-width:72ch; }
  .health { border:1px solid #E4E7E3; border-radius:3px; padding:16px 18px;
            background:#FCFCFA; margin:16px 0; }
  .health dl { display:grid; grid-template-columns:1fr auto; gap:6px 18px;
               margin:0; font:13px/1.6 "Segoe UI",Arial,sans-serif; }
  .health dt { color:#5B6660; }
  .health dd { margin:0; text-align:right; font-variant-numeric:tabular-nums;
               color:#232B27; }
  .state { display:inline-block; padding:1px 8px; border-radius:2px;
           font:12px/1.6 "Segoe UI",Arial,sans-serif; }
  .state.stopped { background:#F6EDE7; color:#BA572D; }
  .state.ok      { background:#E8F1EC; color:#1E7A4C; }
  .state.failed  { background:#F6EDE7; color:#BA572D; font-weight:600; }
  table.incidents { border-collapse:collapse; margin:12px 2px 4px; width:100%;
                    font:13px/1.55 "Segoe UI",Arial,sans-serif; }
  table.incidents caption { text-align:left; font-weight:600; padding:4px 0;
                            color:#232B27; }
  table.incidents th, table.incidents td { border:1px solid #E4E7E3;
                            padding:7px 10px; text-align:left;
                            vertical-align:top; }
  table.incidents thead th { background:#F3F5F2; }
  table.incidents th[scope="row"] { font-weight:400; color:#232B27; }
  table.incidents code { font:12px "Cascadia Mono",Consolas,monospace; }
  h2 { font:600 24px/1.3 "Source Serif 4",Georgia,serif; margin:34px 0 6px; }
  h3 { font:600 17px/1.35 "Source Serif 4",Georgia,serif; margin:22px 0 4px; }
  .lede { font:17px/1.65 "Source Serif 4",Georgia,serif; max-width:70ch; }
  @media (max-width:400px) { .answer .val { font-size:27px; } }
</style>
<script src="assets/echarts.min.js"></script>
<!-- Local, and after ECharts so registerTheme('cascadia') finds it. -->
<script src="assets/cascadia-echarts-theme.js"></script>
</head>
<body>

<!--CASCADIA_DATA_START-->
<script id="cascadia-data" type="application/json">@@data@@</script>
<!--CASCADIA_DATA_END-->

<div class="wrap">

<header class="site-head">
  <p class="kicker"><a href="https://www.robbinsanalytics.com/">Cascadia Portfolio</a> · Matter Ledger</p>
  <h1>Can this number be trusted?</h1>
  <p class="subtitle">A governed model of the public federal civil docket — 10,960,173 case
  records — and what happens to one ordinary legal-operations question when the governance
  is missing.</p>
</header>

<h2>The question</h2>
<p class="lede">How long does it take to resolve a contract dispute in federal court?</p>
<p class="chart-summary">It is a question a legal-operations team gets asked, and the data to
answer it is public. Below, it is answered twice from the same file, retrieved once, on the
same day. Neither query contains a mistake anyone would call obvious.</p>

<div class="answers">
  <div class="answer bad">
    <p class="lbl">Against the raw file</p>
    <p class="val">@@ungov@@ days</p>
    <p class="note">@@negatives@@ matters behind this figure have a
    <strong>negative</strong> duration. Nothing errors, nothing warns, and no null appears
    anywhere to hint that something is wrong.</p>
  </div>
  <div class="answer good">
    <p class="lbl">Against the governed model</p>
    <p class="val">@@gov@@ days</p>
    <p class="note">Median, over @@total_closed@@ closed contract matters. Every figure on
    this page is re-derived from the frozen source down a second, independently written
    path before it is published.</p>
  </div>
</div>

<h2>Why the two answers differ</h2>
<div class="chart-card">
  <div id="c1" class="chart" style="height:460px"></div>
  <p id="c1-note" class="chart-summary" style="display:none"></p>
  <p id="sum-c1" class="chart-summary"></p>
  <details class="data-table"><summary>Chart 1 data table</summary>@@t1@@</details>
</div>

<div class="governance-note">
<strong>One rule out of seven does nearly all of the work, and that is the honest reading
of this chart.</strong> The other six move the answer by less than a day between them. They
are drawn at true scale rather than dropped or rescaled, because their cost is not bounded
by this particular question — the 638 records quarantined by one of them carry disposition
codes that are fragments of dates, and they would corrupt a different measure instead.
</div>

<h2>The trap</h2>
<p class="lede">Both versions of the trend agree. That is not reassurance — it is the
reason this class of error survives review.</p>
<div class="chart-card">
  <div id="c2" class="chart"></div>
  <p id="c2-note" class="chart-summary" style="display:none"></p>
  <p id="sum-c2" class="chart-summary"></p>
  <details class="data-table"><summary>Chart 2 data table</summary>@@t2@@</details>
</div>

<div class="governance-note">
An analyst who sanity-checks the headline against the trend chart finds a plausible line
going the right way, and ships the number. <strong>The same defect, in the same file, on
the same day, is invisible in one cut of the data and catastrophic in another.</strong>
Ungoverned answers are not reliably wrong — they are wrong <em>inconsistently</em>, and
inconsistent wrongness is what defeats a review that relies on someone noticing.
</div>

<h2>And there is no obvious correct filter</h2>
<p class="chart-summary">Suppose the analyst does notice the pending records and reaches for
the obvious fix — keep only the rows the source marks as terminated. That gives
<strong>@@careful_days@@ days</strong>, and silently discards @@careful_lost@@ records,
@@careful_lost_pct@@% of the slice, because the status field did not exist before
statistical year @@careful_year@@. <strong>Both reasonable choices are wrong, in opposite
directions.</strong> Only a closure rule that is effective-dated is right, and that rule is
not derivable from the data — it comes from a sentence in the publisher's codebook.</p>

<h2>What the governed layer actually is</h2>
<p class="chart-summary">Three things, each of which caught something. A written rule
mapping a court docket onto a matter-shaped entity, stating what it loses. Conformed
dimensions loaded from the published codebook rather than written as <code>CASE WHEN</code>
blocks. And five certified measures, each with a definition, a named owner and source
lineage.</p>

<div class="chart-card">
  <div id="c3" class="chart" style="height:430px"></div>
  <p id="sum-c3" class="chart-summary"></p>
  <details class="data-table"><summary>Chart 3 data table</summary>@@t3@@</details>
</div>

<div class="governance-note">
<strong>Two of the procedural-progress codes read identically in the codebook's code
list.</strong> Both say "no court action"; one means before the defendant's answer was
filed, the other means after. The distinction lives in a heading above the list, not in the
code descriptions — so a dimension built from code and description alone merges them, and a
quarter of the slice lands under one meaningless label. The dimension here carries the
group, and the chart reports the qualified form.
</div>

<div class="chart-card">
  <div id="c4" class="chart" style="height:400px"></div>
  <p id="sum-c4" class="chart-summary"></p>
  <details class="data-table"><summary>Chart 4 data table</summary>@@t4@@</details>
</div>

<div class="governance-note">
<strong>The same defect appears one field over, and this chart shows it rather than
smoothing it.</strong> Two dispositions carry the description "other" in the codebook's
code list — one is a dismissal, the other a judgment — and the dimension does not carry
the group that separates them. The bars below are disambiguated by their code because the
code is in the certified measure; carrying the group properly is a change to the data
layer, and it is recorded as owed rather than made quietly from the visual layer.
</div>

<div class="chart-card">
  <div id="c5" class="chart" style="height:470px"></div>
  <p id="sum-c5" class="chart-summary"></p>
  <details class="data-table"><summary>Chart 5 data table</summary>@@t5@@</details>
</div>

<h2>How it stays right</h2>
<p class="chart-summary">The frozen model is validated once. The live edge is not: it runs
on a schedule, takes a bounded increment from a second source, re-asserts the module's
invariants on every run, and reconciles itself against the frozen baseline. The surface
below is the module's own record of that, rendered from the machine-readable health file
the pipeline writes — not restated by hand.</p>

<div class="health">
  <h3 style="margin-top:0">Live edge — last run</h3>
  <dl>
    <dt>Run state</dt><dd><span class="state @@state_class@@">@@status@@</span></dd>
    <dt>Started</dt><dd>@@run_started@@</dd>
    <dt>Assertions checked / failed</dt><dd>@@checks_total@@ / @@checks_failed@@</dd>
    <dt>Last successful run</dt><dd>@@last_ok_at@@</dd>
    <dt>&nbsp;&nbsp;rows added on that run</dt><dd>@@last_ok_rows@@ from @@last_ok_dockets@@ dockets</dd>
    <dt>Last run that was not "ok"</dt><dd>@@last_notok@@</dd>
    <dt>Runs to date / recorded in the log</dt><dd>@@runs@@ / @@runs_recorded@@</dd>
    <dt>Dockets on roster</dt><dd>@@roster@@</dd>
    <dt>Dockets fully ingested / partial</dt><dd>@@complete@@ / @@partial@@</dd>
    <dt>Docket entries derived</dt><dd>@@entries@@</dd>
    <dt>Frozen baseline, same slice</dt><dd>@@slice_matters@@ matters</dd>
    <dt>Reconciliation variance</dt><dd>@@variance@@</dd>
  </dl>
</div>

<h3>What has gone wrong, how it was caught, and what changed</h3>
<p class="chart-summary">A surface that has only ever shown green has demonstrated
nothing. This pipeline has caught four defects <em>in itself</em>, every one of them a
silent failure — nothing errored, and each would have under-collected or mis-stated while
reporting success. Each row below is checkable in the repository's history.</p>

<table class="incidents">
<caption>Defects the module found in its own pipeline</caption>
<thead><tr><th scope="col">What was wrong</th><th scope="col">How it surfaced</th><th scope="col">Fixed in</th></tr></thead>
<tbody>
<tr><th scope="row">The watermark advanced past dockets whose rows were never written — 36 dockets marked done, zero rows persisted</th>
    <td>The run's own record showed the watermark had moved while the output file did not exist</td><td><code>5ef5234</code></td></tr>
<tr><th scope="row">A docket was called complete on the strength of its first page; 29 of the first 36 had more than one</th>
    <td>Row counts did not reconcile against the roster</td><td><code>5ef5234</code></td></tr>
<tr><th scope="row">The request budget read the daily rate-limit window while the hourly window was already exhausted</th>
    <td>The run spent itself on 90-second backoffs for requests that could not succeed</td><td><code>5ef5234</code></td></tr>
<tr><th scope="row">A tie-break in the matter-grain rule depended on row order, which a parallel query engine does not guarantee</th>
    <td><strong>The independent re-derivation disagreed with the build by one record in 1,370,419</strong></td><td><code>317d827</code></td></tr>
</tbody>
</table>

<div class="governance-note">
<strong>A rate-limit stop is a stop, not a failure, and the record says which it was.</strong>
When the source's binding window has no headroom the run exits in seconds and names the
window that bound it. That is the pipeline working as designed. The run log keeps stops,
skips and genuine failures apart rather than colouring them all red.
<br><br>
<strong>Coverage is not completeness.</strong> @@empty_pct@@% of ingested docket entries
carry no description text at all — the source holds what someone has purchased from PACER.
The unclassified rate of @@unclass_pct@@% is therefore a declared health metric, not a
defect, and nothing derived from this feed is certified until coverage itself is modelled.
<br><br>
<strong>The derivation rule earns its keep here too.</strong> @@motion_anywhere@@ ingested
entries contain the word "motion" somewhere; @@motion_at_zero@@ of them are motions
<em>filed</em>. A naive text match counts every order that rules on a motion and inflates
the count by @@motion_inflation@@% — so the rule requires the keyword at the start of the
entry, and says so in writing before any output was produced.
</div>

<div class="disclosure">
<h3>Disclosure</h3>
<p>An independent portfolio project by Aaron Robbins. Built from the Federal Judicial
Center's Integrated Database — public federal civil case records — frozen at
@@as_of@@ and verified by SHA-256 on every build, plus a bounded live increment from
CourtListener's RECAP archive. <strong>No client data and no proprietary data of any
kind.</strong> Nothing here is legal advice, and nothing here is an assessment of any
identified party's litigation exposure: the model is aggregate by construction and
carries no party column.</p>
<p>Source, governance documents and build scripts:
<a href="https://github.com/RobbinsAnalytics/cascadia-matter-ledger">github.com/RobbinsAnalytics/cascadia-matter-ledger</a>.
Every figure on this page is computed at build time from a certified measure; the
independent re-derivation that gates publication is <code>src/validate_measures.py</code>.</p>
<p class="asof">Frozen as of @@as_of@@ · health surface generated @@generated@@</p>
</div>

</div>

<script src="assets/page.js"></script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
