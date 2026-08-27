# The live edge — design, and the four rules running it produced

*Stage 5 artifact. Owner: Aaron Robbins. Established 2026-08-26.*

The frozen snapshot is the baseline. The live edge is the increment. This
document is how the increment is taken, and every rule in it exists because
running the pipeline disproved something simpler.

---

## The slice

| | |
|---|---|
| **Source** | CourtListener REST API v4, RECAP/PACER data |
| **Court** | `cand` — U.S. District Court, N.D. Cal. IDB `CIRCUIT = 9`, `DISTRICT = 71` |
| **Nature of suit** | `190` — the source renders it `190 Contract: Other`, matching the frozen model's largest contract code exactly |
| **Window** | Dockets filed on or after 2024-01-01 |
| **Grain** | One row per docket entry, classified per `docket-event-derivation.md` R-05 |

**One court, deliberately.** Clerk conventions differ between districts, so a
vocabulary calibrated on one court is not automatically valid in another. See
`docket-event-derivation.md` D-03.

## The shape, and why it is not the obvious one

The obvious query asks for docket entries filtered by the parent docket's court
*and* nature of suit in a single request. **It times out server-side after 150
seconds.** Filtering entries by `docket=<id>`, a direct foreign key, returns in
about 0.3 seconds.

So the pull is two phases: build a roster of dockets in the slice, then walk the
roster one docket at a time. That spends more requests and roughly 500× less
wall clock, and it is the only shape that completes at all.

---

## W-01 · The watermark says what has been SEEN, not what is COMPLETE

The watermark is the highest docket id below which nothing is unseen. That is a
weaker claim than "everything below here is finished", and the two must never be
conflated. Dockets that were seen but not finished live in a separate
`partial_dockets` map with the cursor needed to resume them, and **they are
revisited on every run regardless of the watermark.**

## W-02 · Persist before advancing. Never the other way round

*Found by running it.*

The first version advanced the watermark inside the walk and wrote the derived
rows once, at the end. Run 1 walked 36 dockets, advanced the watermark past all
36, hit an HTTP 429, took the failure path — and wrote **no rows at all**.

The watermark said those dockets were done. The output file did not exist. The
run record said "failed" without saying what had been skipped, and the next run
would have resumed past 36 dockets that appear nowhere in any output.

Only the permanent response cache made it recoverable, and **a cache is a
performance decision, not a durability guarantee.** Rows are now written and
fsynced before the watermark moves, per docket.

> A watermark that can advance past unpersisted work is a data-loss bug, and it
> is invisible: nothing errors, and the missing records leave no hole to notice.

## W-03 · A docket is done only when its entry list is exhausted

*Found by running it.*

Entries are returned 20 at a time and the `page_size` parameter is ignored.
**29 of the first 36 dockets have more than one page.** The first version took
page one, logged a note, and advanced the watermark — claiming complete coverage
of dockets it had seen twenty entries of.

A docket is now paged to exhaustion or recorded as partial with its resume
cursor. It is never counted as complete on the strength of one page.

## W-04 · Budget from the binding window, not the one you remember

*Found by running it.*

Three limits apply concurrently — 5/minute, 50/hour, 125/day — and the most
restrictive controls. The first version budgeted from the daily figure alone,
computed a budget of 50 requests while the hourly window stood at 50/50, and
spent the run absorbing 90-second backoffs to make requests that could not
succeed.

The budget is now the minimum across all three windows, read from the API's own
usage endpoint, which has an independent throttle and costs nothing to call. A
run with no headroom exits in seconds and says which window bound it.

**Pacing:** 15 seconds between requests. 12.5s was tried and produced a 429 on
the first run — the window is *rolling*, so requests made before the process
started are still inside it. Pacing to the arithmetic limit leaves no room for
what came before.

---

## Where the schedule lives, named explicitly

The job runs from the **Code scheduled-task store**,
`C:\Users\Ajayr\.claude\scheduled-tasks\cascadia-matter-ledger-live-edge\`,
twice daily at 07:00 and 19:00 local, cron `0 7,19 * * *`.

**Two stores exist on this machine and neither tool indicates the other does.**
Cowork reads `C:\Users\Ajayr\Claude\Scheduled\`. This job is not there. Naming
the store is a house rule precisely because saying "the scheduled task" without
one has cost a session.

The task's `SKILL.md` is the only copy — it is **not** mirrored into this repo,
deliberately. A second copy that nobody updates is the drift problem one level
up, and the store is what actually runs.

The token reaches the job as a **user-scope environment variable**, which a
process launched under Aaron's account inherits. It is never written to a file
in this repository and the `.githooks/secret_scan.py` gate would refuse the
commit if it were.

## What a run guarantees

| Property | How |
|---|---|
| Never re-fetches | Every response is cached by URL hash, permanently, and read from there forever after |
| Resumable | Watermark plus per-docket resume cursors; a killed run loses nothing |
| Inside the limit | Budget from the binding window; clean skip when there is no headroom |
| Bounded | Hard ceiling of 55 requests per run, and a 25-request daily reserve, so one run cannot consume the day |
| Honest about coverage | Completed and partial dockets are counted separately and both are published |
| Fails loudly | Every run writes `governance/last_live_run.json` with each check and its result |

## What a run does NOT guarantee

**Coverage is not completeness.** RECAP holds what someone has purchased or
contributed from PACER. **65.6% of ingested entries have no description text at
all.** A docket with few entries here may be a quiet docket or a poorly covered
one, and the pipeline cannot distinguish them. Every figure derived from this
source is *observed* activity, never *all* activity, and nothing derived from it
is certified in `metric_register.md` until coverage itself is modelled.

That limit is a property of the source. It is stated here rather than discovered
later by a reader.
