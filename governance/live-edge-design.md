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

## W-05 · The roster's stop condition must be provable, not conceded

*Found by running it. Three consecutive runs died of this.*

The roster was enumerated by descending keyset pagination on `id`, and its
only exit was the API returning `next: null`. To say that, the server has to
scan to id 0 through `nature_of_suit__istartswith=190` — an unindexed text
match across ~68 million rows. **It cannot, and it does not:** the query
returns HTTP 504 after roughly 180 seconds, every time. The client's 120s
timeout fires first, so three runs reported a read timeout and a 502 and none
of them named the cause.

The roster was never missing anything. It had already collected every docket
above its own minimum and was grinding through id space that predates the
slice, unable to prove a negative.

Measured 2026-08-29, one request each:

| query | result |
|---|---|
| unbounded descent at the stored cursor | **HTTP 504 after 180.3s** |
| bounded month window, 2025-06 | 200 in 103.2s |
| bounded month window, 2024-01 | **HTTP 504 after 180.3s** |
| **500,000-id window with the same filters** | **200 in 4.3s** |

Date windowing does not rescue it. Bounding by `id` does, because `id` is
indexed and the filter then applies to a bounded scan.

**The floor is derived, never typed.** A docket row cannot be created before
the case it describes is filed, so every docket filed on or after the slice
start has an id above the last id created before it. That id is asked for
directly — one request, `date_created__lt=<slice start>`, ordered by
descending `id`. In this court it is **68,128,452**, created 2023-12-31.
The roster's own minimum, after the descent finally ran to the floor, is
**68,130,085** — 1,633 ids above it. The floor is tight and it is checked
against that minimum on every derivation.

**What the floor rests on, stated rather than assumed.** It is sound only if
id order is monotonic with creation order across that boundary. The unbounded
form of that question times out like everything else here, so it was asked of
the 500,000 ids immediately below the floor, where a violation would most
plausibly sit: nothing there is filed inside the slice, and nothing there was
created after the slice opened. **Bands further down are unverified.** If the
source ever backfills a docket with an out-of-order id, this floor would hide
it. The floor is therefore recorded in state with the date it was derived,
rather than being silently recomputed.

**Completion made a second defect reachable.** `roster_complete` is terminal —
the enumerating loop is skipped forever once it is set. That was harmless only
while completion was impossible. On the first run after the roster completed,
discovery would have stopped dead and the live edge would have quietly stopped
being live, with nothing erroring. The top of the id range is now swept every
run, bounded below by the highest id already known, which is the cheap
direction.

> A stop condition that depends on the source conceding is not a stop
> condition. It is a hope, and this one was false for three runs.

## W-06 · The permanent cache disabled discovery, and the fix for W-05 is what made it reachable

*Found by running it. Discovery was dead for two days and every run passed.*

W-05 ends by saying the top of the id range is now swept every run, bounded
below by the highest id already known. That sweep was written, is correct, and
**never executed after 2026-08-29 15:46.**

The sweep's URL is `id__gt=<max(roster)>&order_by=id`. Its bound is the answer
to the previous sweep. The response cache is keyed by URL and, before this
entry, was permanent with no exceptions — so the two locked against each other:

- the URL cannot change until the sweep returns a docket, and
- the sweep cannot return a docket, because it is being handed a stored empty
  page instead of being sent.

The cached page was written 2026-08-29 15:46:54 with `results: []` and
`next: null`. **Every run after it replayed that page, for free, and reported
`roster top-up, newly created dockets 0`.** No request was sent, no quota was
spent, no check failed, and the run record said `ok`. The live edge was not
running slowly. It was not running.

**The cache is exempted for this one query and must stay exempted.** A docket
entry page is immutable and caching it forever is right; a discovery query's
whole purpose is to return something it did not return last time. The exemption
is `refresh=True`, bounded to at most two pages per run.

> A cache keyed on a value the cache itself determines is not a cache. It is a
> latch, and this one was closed for eight runs.

## W-07 · `id > watermark` cannot express "not yet walked", and W-01 said so

*Found by running it. It stranded 238 of 332 dockets.*

W-01 states the rule at the top of this document: the watermark says what has
been **seen**, not what is **complete**. The walk then selected its worklist as
`id > watermark`, which is precisely the conflation W-01 forbids, and the
comment above that line restated the rule without acting on it.

The two phases move in opposite directions. The roster descends toward the id
floor; the walk ascends. So every docket the descent discovered was added
*below* a watermark the walk had already carried upward — and `id > watermark`
can never select it again. The only re-entry path for a docket below the
watermark is `partial_dockets`, and **a docket that was never started is not
partial. It is absent.** Nothing errored, because nothing was wrong from the
watermark's point of view.

**It hid itself while it was still doing work.** The walk kept completing
dockets as long as any roster id sat above the watermark — 26 on the 21:28 run,
6 on 22:39, 6 on 2026-08-30 15:41. It reached zero only on 2026-08-31, when the
watermark reached the roster maximum (74,669,274) and the worklist became
permanently empty. A run reporting six dockets was already stranding the ones
below it.

**Completion is now recorded, not inferred.** `dockets_ingested` holds the
dockets whose entry list has been exhausted, written at the moment it is
exhausted. The worklist is `roster − ingested − partial`. The watermark is kept
for the one claim it can support — nothing above it is unseen — and is no
longer a completeness test.

Two consequences worth stating:

- **Order is edge first, then backfill.** Newly discovered dockets are walked
  ahead of the backlog. Ascending order would have buried a newly filed docket
  behind roughly ten runs of backfill, which would satisfy the code and defeat
  the module.
- **`dockets_remaining` is now published in `health.json`.** Its absence is why
  a stalled backfill read as healthy: `dockets_fully_ingested: 94` beside
  `roster_dockets: 332` is the same fact, and nobody has to subtract to see it.

> The rule was written down first and violated four lines below it. Stating an
> invariant in prose does not enforce it; the selection has to be unable to
> express the wrong thing.

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
| Terminates | The roster is enumerated to a derived id floor, so completion is provable rather than conceded by the source — W-05 |
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
