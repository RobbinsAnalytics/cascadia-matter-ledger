# Chart review — Cascadia Matter Ledger

*Visual layer, five detailed charts. Owner: Aaron Robbins.*
*First review 2026-08-26; second round after Aaron's read of the renders, 2026-08-28.*

**Binding standard, confirmed on disk and quoted by version:**

| Document | Version | Path |
|---|---|---|
| `VIZ-PRINCIPLES.md` | **v2.7 — August 2026** | `cascadia-standards/design-system/` |
| `CHART-REVIEW.md` | **v2.7** (companion to VIZ-PRINCIPLES v2.7) | `cascadia-standards/design-system/` |

The repo copies are canonical and are what this build was reviewed against.

**Quadrant: EXPLANATORY. Checklist A applies in full.** No reader controls of
any kind — no filters, selectors or tabs. Adding one would move the artifact
into Checklist B.

**Chart class: all five are detailed charts**, read for values. No signature
charts.

---

## 0 · READING PANEL (Rule 7.4) — 2026-08-28

```
READING PANEL — Cascadia Matter Ledger visual layer — 2026-08-28
Decision served (Rule 0.1): a legal-operations leader deciding whether a
  reported number can be trusted — and by extension whether the person who
  produced it should be trusted to build the layer that produces it.
  Horizon: tactical. Not a live console, not a strategy deck.
Charts panelled: 5   States: default only (the page has no reader controls)
Nature: simulated

  Seat 1  Senior Director of Legal Affairs, controls background (Arthur
          Andersen, then accounting programs and controls, then legal
          operational compliance), 18 years — simulated — why this seat:
          she is the one who has to decide whether to trust the number, and
          she decides it the way a controls person does: is there evidence,
          is there an owner, could this be wrong for a long time before
          anyone noticed. Not a technologist and not a lawyer.
  Seat 2  Senior Manager, Legal Technology Operations, 26 years in legal
          systems, has built matter management and e-billing integrations —
          simulated — why this seat: he is the person in the room who knows
          how a matter is actually opened, worked and closed, and the
          decision turns on whether this model's vocabulary survives contact
          with that. He is also the one who can say whether a number is
          reproducible from a system of record.
  Seat 3  Legal Operations Manager who owns the outside-counsel budget,
          9 years, not an analyst — simulated — why this seat: the decision
          is only worth making if something downstream changes, and he is
          downstream. He also sits where the room's actual literacy sits;
          the other two are practitioners and would flatter the artifact.
  Seat 4  visualization reader — simulated — canvas only; tables and
          arithmetic excluded

Blindness asserted: design system [x] · review and build notes [x] ·
                    source data [x] · intended finding from outside the
                    artifact [x] · other seats' output [x]
Run: parallel [x]   Author's pre-panel notes recorded: [x]
                    (governance/pre-panel-notes.md, 14 suspicions, written
                     before any seat was spawned — required to compute N)

Widths given to every seat: 1040 px viewport (chart element 1000 CSS px)
                       AND   320 px viewport (chart element 280 CSS px).
Seats were told the second set was "as it appears on a phone" and asked to
say where the two differed.

What this record cannot verify about itself: blindness and parallelism are
self-attestation. Running the panel through the skill makes them properties
of the code path rather than of anyone's memory, but the document still only
records an assertion. Every seat was spawned in a single message, given only
the ten PNG paths, and instructed to read no other file on the machine.
```

### Per-seat returns

Verbatim. Not tidied — a cleaned quote is the author's paraphrase in quotation marks.

**Seat 1 · Senior Director, Legal Affairs**

| Chart | Item | Verbatim |
|---|---|---|
| 1 | sentence | *"This is walking through how you get from a nonsense negative number to a real answer of 208 days ... and it's basically one correction — pulling out the still-open cases — that does almost all the work."* → carries the title's claim: **yes** |
| 1 | number | *"The last bar, labeled 'The governed answer,' reads 208"* — located at: **data label on a mark** |
| 1 | question | *"who approved that exclusion rule, and is it written down somewhere I could point to if someone asked me to defend it?"* |
| 1 | gap | *"I didn't see who owns this, or a date it was approved. And there's no range or confidence interval on 208"* |
| 2 | sentence | *"Both lines say the same thing directionally ... but they're two different calculation methods sitting 100 days apart from each other the whole time."* → **yes** |
| 2 | number | *"The label at the end of the solid green line says 'Governed median, 263 days'"* — **end-of-series label** |
| 2 | question | *"If we know the orange line (the mean) is the wrong method, why is it still on the chart at all"* |
| 2 | gap | *"I looked for the broken/pending records that get excluded and couldn't find them anywhere on the chart"* |
| 3 | sentence | *"A big share of our contract cases — over 40% — are wrapping up before the two sides have even formally locked in what they're fighting about"* → **yes** |
| 3 | number | *"The top bar, 'other (after issue),' is labeled 254,521"* — **data label on a mark** |
| 3 | question | *"That top category, 'other (after issue)' — the single biggest bucket on the whole chart — what's actually in it? The label doesn't tell me."* |
| 3 | gap | *"none of the individual bars are labeled with a percent — just raw counts — so I'd have to do that division myself"* |
| 4 | sentence | *"How long a contract dispute takes really depends on what kind of contract dispute it is"* → **yes** |
| 4 | number | *"The bottom bar, Contract Product Liability, is labeled 307 d"* — **data label on a mark** |
| 4 | question | *"am I supposed to have the same confidence in a median built on 5,032 cases as one built on half a million?"* |
| 4 | gap | *"There's no spread shown — no range, no percentile band, just a single median number per category."* |
| 5 | sentence | *"The overwhelming majority of these cases end by settlement or dismissal, not trial"* → **yes** |
| 5 | number | *"The top bar, 'settled,' is labeled 30.7%"* — **data label on a mark** |
| 5 | question | *"What's the actual difference between 'settled' at 30.7% and 'voluntarily' dismissed at 16.4%"* |
| 5 | gap | *"The bars only show percentages, not counts."* |

**Seat 2 · Senior Manager, Legal Technology Operations**

| Chart | Item | Verbatim |
|---|---|---|
| 1 | sentence | *"if you just ran the obvious query against this docket file you'd get a negative cycle time, and it takes one specific fix ... to get you to a number you could put in front of anyone"* → **yes** |
| 1 | number | *"The label on the 'governed answer' bar at the bottom reads 208 — ... I got it off the bar itself, not the table."* — **data label** |
| 1 | question | *"has anyone spot-checked a sample of the 'excluded' records to confirm they're genuinely still open and not just missing data?"* |
| 1 | gap | *"I looked for a case count or n= somewhere on this chart — how many matters this waterfall is actually built on — and didn't find one."* |
| 2 | sentence | *"Two cycle-time trend lines that move together ... but the chart's own headline is warning me not to trust the top line"* → **yes** |
| 2 | number | *"'Governed median, 263 days' — ... taken from the label at the right end of the solid green line"* — **end-of-series label** |
| 2 | question | *"is the ungoverned mean still being reported anywhere downstream, and if so can we kill that feed"* |
| 2 | gap | *"I looked for the pending-case volume — how many records actually carry that statistical year 2099 sentinel and get dropped — and it isn't on this chart"* |
| 3 | sentence | *"Of everything that closes, a big share never even gets to the point where the parties are contesting the merits"* → **yes** |
| 3 | number | *"The top bar, 'other (after issue),' is labeled 254,521"* — **data label** |
| 3 | question | *"What's actually inside 'other (after issue)' at 254,521 — that's the single largest bucket and the label tells me nothing about what it contains"* |
| 3 | gap | *"I looked for a total matter count to sanity check the 43% claim against and didn't find one on the chart itself"* |
| 4 | sentence | *"Contract case types resolve at very different speeds ... and the chart is upfront that the categories aren't the same size."* → **yes** |
| 4 | number | *"the bottom bar, Contract Product Liability, is labeled 307 d, with (n=13,652) printed right under the category name"* — **data label + axis label** |
| 4 | question | *"what actually falls into 'other,' and is that category so large it's masking meaningful sub-patterns"* |
| 4 | gap | *"I looked for any variance or spread measure — an IQR, a range — beyond the single median dot per category, and didn't find one"* |
| 5 | sentence | *"settlement is the single biggest way these end, with trial of any kind being a rounding error"* → **yes** |
| 5 | number | *"The top bar, 'settled,' is labeled 30.7%"* — **data label** |
| 5 | question | *"what does our own department's characterization of these same matters look like, and how far off is it from the court's"* |
| 5 | gap | *"I looked for a 'trial' rollup (jury verdict + court trial combined) ... I'd have to add them myself"* |

**Seat 3 · Legal Operations Manager, outside-counsel budget**

| Chart | Item | Verbatim |
|---|---|---|
| 1 | sentence | *"This is somebody showing me their homework on how they cleaned up a data question, not a budget chart"* → **partly** — carries the method, not the finding |
| 1 | number | *"The label on the green bar next to '4. exclude pending matters' said +1062"* — **data label** |
| 1 | question | *"Forget the seven-step tour — what's the number I should actually be quoting, 208 days?"* |
| 1 | gap | *"There's no dollar figure anywhere on this. I own a budget, and this whole thing is about counting days, not cost."* |
| 2 | sentence | *"Whichever way you measure it, contract cases are taking longer to close than they used to."* → **yes** |
| 2 | number | *"The label at the right end of the solid green line said 263 days."* — **end-of-series label** |
| 2 | question | *"Which of these two lines is the one I should be plugging into next quarter's forecast — and why would you ever hand me the 'wrong' one at all?"* |
| 2 | gap | *"No year-over-year percentage, no cost-per-day, nothing that turns 'days' into dollars for me."* |
| 2 | **phone** | *"On the phone those labels are gone — the lines just end with no text ... If I only had ten seconds on my phone I'd have missed the actual numbers entirely."* |
| 3 | sentence | *"A big chunk of these cases never even get to the point where both sides have actually joined issue before they're closed out."* → **yes** |
| 3 | number | *"the 43% in the headline isn't on any single bar — I only found it in the sentence underneath the chart"* — **could not source it from the plot** |
| 3 | question | *"how many of those were cheap, fast dismissals versus ones where we'd already paid a firm real money"* |
| 3 | gap | *"Nothing here tells me whose matters these are — ours, or every contract case filed in federal court."* |
| 4 | sentence | *"How long a contract case takes depends a lot on what kind of contract dispute it is"* → **yes** |
| 4 | number | *"The top bar, Vet Benefit overpayments, was labeled 98 d"* — **data label** |
| 4 | question | *"Which of these categories actually map to the kinds of matters we send outside counsel"* |
| 4 | gap | *"no spend, no rate, nothing that lets me translate 'days' into 'budget.'"* |
| 5 | sentence | *"Almost a third of these settle, and almost nothing goes all the way to a jury — which is basically what I'd expect."* → **yes** |
| 5 | number | *"The top bar, 'settled,' was labeled 30.7%"* — **data label** |
| 5 | question | *"Is 30.7% our settlement rate, or the whole federal court system's?"* |
| 5 | gap | *"No settlement value, no fee spend by disposition type"* |

**Seat 4 · Visualization reader (canvas only)**

| Chart | Item | Verbatim |
|---|---|---|
| 1 | title vs picture | *"All three clauses of the title are directly readable off the chart; nothing here needs to be taken on faith."* |
| 1 | form | *"A waterfall is exactly the form for 'here's a sequence of adjustments that bridge a start value to an end value.'"* |
| 1 | hard to read | *"The floating text has no leader line pointing to what it explains, so it reads as generic commentary rather than an annotation of a specific bar."* |
| 1 | grayscale | *"Yes. Sign is doubly encoded — bar direction ... plus an explicit printed number on every bar"* |
| 1 | number | *"+1,062 days, read off the labeled green bar"* — **data label** |
| 2 | title vs picture | *"the specific magnitude '1,062 days' isn't plotted anywhere here — it's imported from Chart 1. A reader looking at Chart 2 alone has to take the second half of the title entirely on faith."* |
| 2 | form | *"two smooth, parallel, plausible-looking lines that never diverge or spike is visually reassuring, not alarming ... Form and claim pull in different directions here."* |
| 2 | hard to read | *"at this width the plot has no legend or in-chart labels at all ... the chart image alone, at phone width, no longer identifies its own series."* |
| 2 | grayscale | *"Yes — dash-pattern ... is a redundant encoding alongside colour"* |
| 2 | number | *"362 days for 'Ungoverned mean,' read at the right-hand endpoint label"* — **end-of-series label** |
| 3 | title vs picture | *"The '43%' is not drawn anywhere on the chart — no bracket, no shaded region, no subtotal bar, and bars are labeled with raw counts, not percentages ... this is the weakest title-to-image link of the five charts."* |
| 3 | form | *"the chart is drawn as an unaggregated, single-color ranking of 13 categories with no grouping, split coloring, or subtotal ... the form supports 'here's a ranked list of stages' much better than it supports '43% happens before X.'"* |
| 3 | hard to read | *"the three smallest bars ... shrink to slivers only a few pixels wide"* (320 px) |
| 3 | grayscale | *"Trivially yes — every bar is the same single green ... this also means the chart never uses colour to do the one job that would have helped"* |
| 3 | number | *"254,521 for 'other (after issue),' the longest bar"* — **data label** |
| 4 | title vs picture | *"Nothing here requires outside arithmetic or faith — this is the cleanest title-to-image match of the five."* |
| 4 | form | *"Yes — a sorted bar chart is the natural form for 'here is a range across categories.'"* |
| 4 | hard to read | *"the same category carries different text depending on viewport, which would be confusing if someone tried to cite or cross-reference a category name"* |
| 4 | grayscale | *"Yes — single-color bars throughout"* |
| 4 | number | *"307 days for 'Contract Product Liability' (n=13,652)"* — **data label** |
| 5 | title vs picture | *"Both headline numbers are directly plotted and labeled"* — but *"the claim 'near the bottom of the ranking' ... is not literally the bottom, since five smaller categories sit below it."* |
| 5 | form | *"Yes for a ranked-share breakdown across many categories"* |
| 5 | hard to read | *"The bottom several categories ... collapse to bars so thin they're effectively invisible"* |
| 5 | grayscale | *"Trivially yes"* |
| 5 | number | *"30.7% for 'settled,' read from the top bar's label"* — **data label** |

### Disposition

Sorted by seat count. Convergence drives fix order: four blind readers falling
into the same hole from four directions outranks one eloquent objection.

| # | Finding, in the reviewer's words | Seats | n | Chart | Defect? | Novel? | Disposition | Rule |
|---|---|---|---|---|---|---|---|---|
| 1 | *"The '43%' is not drawn anywhere on the chart — no bracket, no shaded region, no subtotal bar, and bars are labeled with raw counts, not percentages"* | 1,2,3,4 | **4** | 3 | yes | yes | **fixed** — the two groups the claim compares are now separate hues and every bar carries its share as well as its count; the four green bars sum to the headline 43% | 3.2 |
| 2 | *"What's actually inside 'other (after issue)' at 254,521 — that's the single largest bucket and the label tells me nothing about what it contains"* | 1,2 | **2** | 3 | yes | yes | **fixed** — the subtitle states that "Other" is the codebook's own residual category whose contents the source does not specify | 3.2 |
| 3 | *"On the phone those labels are gone — the lines just end with no text"* | 3,4 | **2** | 2 | yes | yes | **fixed** — end-of-line labels restored at every width, abbreviated but never dropped, with a gutter to hold them | 5.5 |
| 4 | *"I looked for any variance or spread measure — an IQR, a range — beyond the single median dot per category, and didn't find one"* | 1,2 | **2** | 4 | yes | yes | **fixed** — the 25th–75th percentile is drawn as a whisker on every bar; the quartiles were in the measure and the table all along but not on the canvas | 4.5 |
| 5 | *"the specific magnitude '1,062 days' isn't plotted anywhere here — it's imported from Chart 1"* | 4 | 1 | 2 | yes | yes | **fixed** — the annotation now names the 32,767 pending records and says they are why the ungoverned answer is negative | 4.3 |
| 6 | *"I looked for a case count or n= somewhere on this chart ... and didn't find one"* | 2 | 1 | 1 | yes | yes | **fixed** — the subtitle states the population the waterfall is built on | 4.3 |
| 7 | *"'near the bottom of the ranking' ... is not literally the bottom, since five smaller categories sit below it"* | 4 | 1 | 5 | yes | yes | **fixed** — the summary states the rank and how many sit below it, computed rather than characterised | 3.2 |
| 8 | *"the phone version's y-axis is compressed into 50-day gridlines instead of 100, which makes the two lines look visually farther apart"* | 2 | 1 | 2 | yes | yes | **fixed** — one axis range at every width; the narrow-only headroom saving is gone | K6 |
| 9 | *"The floating text has no leader line pointing to what it explains, so it reads as generic commentary"* | 4 | 1 | 1 | yes | no | **fixed** — the annotation names the step it explains, so the link survives the distance K3 forced between text and bar | 3.4 |
| 10 | *"Nothing here tells me whose matters these are — ours, or every contract case filed in federal court."* | 3 | 1 | 3 | yes | no | **fixed** — the subtitle states the scope | 4.3 |
| 11 | *"nothing in this set has a dollar sign on it. Every chart is about time or case counts"* | 3 | 1 | all | no | — | **rejected** — the source carries no cost data at all: no spend, no timekeeper, no rate. Recorded as a stated limit in `docket-to-matter.md` L-03. A chart cannot invent it, and the seat's reaction is the strongest argument for stating that limit loudly | — |
| 12 | *"I didn't see who owns this, or a date it was approved"* | 1 | 1 | 1 | no | — | **rejected** — ownership and as-of are page-level, in the disclosure block and the provenance strip. Repeating them on five canvases is not what 4.2 asks for | 4.2 |
| 13 | *"the same category carries different text depending on viewport"* | 4 | 1 | 4 | no | — | **rejected** — a declared abbreviation mapping, which 5.5 permits explicitly and prefers to deleting a label | 5.5 |
| 14 | *"two smooth, parallel, plausible-looking lines that never diverge or spike is visually reassuring, not alarming"* | 4 | 1 | 2 | no | — | **rejected** — that is the finding, not a defect. The chart exists to show that a broken method looks reassuring in this cut | — |
| 15 | *"the near-zero bars ... are compressed to hairlines that are essentially just their number labels with no visible mark"* | 4 | 1 | 1 | no | — | **rejected** — drawn at true scale deliberately; rescaling would hide that five rules move the answer by under a day between them, which is the honest reading | 4.1 |
| 16 | *"The bars only show percentages, not counts."* | 1 | 1 | 5 | no | — | **rejected** — the title makes a percentage claim so the bars carry percentages; counts are in the tooltip and the table, which 4.4 names as the home for full precision | 4.4 |

### Summary

```
PANEL: 4 seats, simulated · 5 charts · findings 16 · defects 10 · novel 8
       fixed 10 · accepted 0 · rejected 6 · multi-seat defects 4
       D = 2.00 defects/chart · N = 0.80 novel share · R = 0.38 rejected share
```

**Reading these numbers honestly.** D = 2.00 is high and N = 0.80 is very high:
four fifths of what the panel found, the author had not written down — and this
is *after* two rounds of the author's own review and two rounds of Aaron's. That
is the case for the rule, not against it.

**The convergence is the result worth keeping.** All four seats independently
reported that Chart 3's headline percentage was nowhere on Chart 3 — both
practitioner seats, the non-analyst seat, and the canvas-only seat, from four
different directions. The author's pre-panel notes worried about the wrong thing
on that chart entirely (a duplicated label) and never saw that the title's claim
was unsupported by the picture.

**The visualization-seat ratio, tracked as the skill asks.** Seat 4 raised 8 of
the 16 findings and 5 of the 10 defects — high, but not the 13-of-19 the Deal
Desk panel recorded. The three domain seats produced 5 defects between them and
several were substantive rather than gaps, including the two that drove the
Chart 4 whisker. The domain floor of three is earning its place so far; one more
module before that conclusion is worth anything.

**On the sentence returns**, which Rule 7.2's DracoGPT caveat says is where this
procedure will fail if it fails: 19 of 20 carried the title's claim, and the one
that did not — Seat 3 on Chart 1, *"somebody showing me their homework"* — was
the most useful sentence in the set, because it is exactly how a budget owner
would describe a methodology chart to a colleague. The sentences were not bland
and did not merely echo the titles.

---

## 1 · Checklist A, per chart

| Check | C1 waterfall | C2 trend | C3 progress | C4 duration | C5 disposition |
|---|---|---|---|---|---|
| 1.2 encoding rank | position, common scale | position | position | position | position |
| 1.3 banked to 45° | n/a | **yes**, `cascadiaBankedHeight` | n/a | n/a | n/a |
| 2.1 baseline governed by the claim | zero on axis — value crosses it | **truncated**, declared in subtitle; the title makes a *difference* claim | zero | zero | zero |
| 2.2 one value axis | yes | **yes, no secondary** | yes | yes | yes |
| 2.3.5 ≤4 encoded categories | 2 (direction) | 2 series | 1 | 1 | 1 |
| 2.3.7 text inks | `CASCADIA.textInk`, imported | imported | imported | imported | imported |
| 3.1 title states the finding | yes, computed | yes, computed | yes, computed | yes, computed | yes, computed |
| 3.4 annotation on the mark | yes | yes | n/a | n/a | n/a |
| 3.6 direct labels, no legend | value labels | **end labels, legend off** | value labels | value labels | value labels |
| 4.2 provenance strip | 3 segments | 3 | 3 | 3 | 3 |
| 5.1 L1 summary + L2 table | both | both | both | both | both |
| 5.1 L3 keyboard | not required | **required — `cascadiaNavigator`** | not required | not required | not required |
| 5.2 description is L1–L3 | yes | yes | yes | yes | yes |
| 5.3 min 12 px | theme floor | theme floor | theme floor | theme floor | theme floor |
| 5.4 monochrome-safe | direction also by position/sign | **dash vs solid + end labels** | single hue | single hue | single hue |
| K2 every figure computed | yes | yes | yes | yes | yes |
| K5 rendered segment count | 3 ✓ | 3 ✓ | 3 ✓ | 3 ✓ | 3 ✓ |

**K5 was verified from the render, not the config** — `src/render_charts.py`
counts the separator in the rendered strip at both widths and prints it.
Both widths returned `[3, 3, 3, 3, 3]`.

## 2 · Findings raised by this review, and their disposition

Every one of these was found by **looking at a render**. None was visible in
the configuration.

| # | Chart | Finding | Disposition |
|---|---|---|---|
| F-1 | C1 | The stacked-bar waterfall drew the opening bar on the **wrong side of zero**. ECharts stacks positive and negative values into separate stacks, so a value crossing zero cannot be a stacked waterfall. | **Fixed** — rewritten as a `custom` series drawing an explicit `[from, to]` span per bar. |
| F-2 | C1 | Value labels printed **over** their bars, two labels missing entirely, and the ink did not follow the bar. `label.position` takes a string, not a callback; the callback silently fell back to a default. | **Fixed** — position and ink set per datum, labels outside the bar end. |
| F-3 | C1 | **K3**: the annotation overlapped step 3's value label. | **Fixed** — moved into free space; at 320 px it leaves the plot entirely per Rule 5.5 step 4. |
| F-4 | C2 | **K3**: the annotation was drawn directly over the dashed series. | **Fixed** — the axis now reserves headroom and the annotation sits in it, which is the remedy K3 names. |
| F-5 | C2 | A zero baseline flattened the shape and defeated the Rule 1.3 banking. | **Fixed** — axis truncated, which Rule 2.1 permits because the title makes a difference claim, and the truncation is declared in the subtitle. |
| F-6 | C3–C5 | At 320 px the value axis **inverted** and the plot collapsed: long category labels plus `grid.right` exceeded the viewport. | **Fixed** — width-aware label column, declared abbreviation mapping, thinned tick density. |
| F-7 | all | At 320 px the wrapped title overran the plot area; a fixed `grid.top` cannot know how many lines a title takes. | **Fixed** — the title block is measured with a canvas text metric and the grid starts below it. |
| F-8 | C3–C5 | At 320 px the x-axis ticks collided into an unreadable run of digits, and the axis units were lost behind them. | **Fixed** — `splitNumber` thinned, declared `k` abbreviation, units never dropped. |
| F-9 | C4 | The topmost category's three-line label was clipped above the plot. | **Fixed** — headroom added rather than the label shortened. |
| F-10 | C5 | **Two dispositions render identically as "other"** — code 14 is a dismissal, code 17 a judgment — because `dim_disp` does not carry the codebook's three-group structure. Same defect class as the procedural-progress codes. | **Disambiguated on the chart by code**, which is in the certified measure, and **reported**. Carrying the group properly is a data-layer change and is recorded as owed, not made from the visual layer. |
| F-11 | health | `governance/health.json` records only the **most recent** run. The brief's §4 asks for the last *successful* run and the last *failure* with its cause; neither is derivable from a single-run record. | **Reported, then closed on 2026-08-28.** An append-only `governance/run_history.jsonl` now records every run, and the surface shows the last successful run and the last run that was not "ok". The log begins where it was added: earlier runs were overwritten in place and are **not** reconstructed, because the module's one genuine HTTP 429 failure cannot be recovered without fabricating it. The failure story is told instead by the incident table, whose four entries are all checkable commits. |

### Second round — Aaron's read of the renders, 2026-08-28

He reviewed the 1040 px renders and raised four chart notes and one on the
health surface. Acting on them exposed five further defects, four of which
only a render shows.

| # | Chart | Finding | Disposition |
|---|---|---|---|
| F-12 | C1 | **Value labels collided with their own bars at ~630 px** — the width Aaron happened to screenshot. A fixed 230 px label column plus a 92 px gutter squeezed the plot until "outside the bar" landed back on it. 630 px sat between the two rendered widths and was therefore never checked. | **Fixed** — label column proportional at every width, and axis padding **measured** from the widest label rather than a constant. 630 px and 768 px added to the verification set. |
| F-13 | C1 | **K1 — three bars ran past the frame.** Axis bounds were taken from the first and last answers, but the running total peaks at 319.8 after step 4 before falling back to 208. The axis stopped at 300, and ECharts silently dropped the labels of every point outside it. | **Fixed** — bounds computed from every span endpoint. |
| F-14 | C1 | **K3 — the annotation overlapped step 3's mark and step 4's bar.** | **Fixed** — moved into the band beside the sub-day steps, whose only marks sit hard against the left edge. Below 900 px it leaves the plot entirely (5.5 step 4). |
| F-15 | C1 | At narrow widths the chart rendered **both** the in-plot annotation and the out-of-plot note — the same sentence twice, one of them over a bar. | **Fixed** — it is one or the other, never both. |
| F-16 | C3 | Two-line category labels made ECharts **auto-hide the first and last categories**: two bars with no name against them, which reads as a chart that lost its data. | **Fixed** — `interval: 0` forces every label; rows given more height. |
| F-17 | C5 | The four smallest dispositions rendered as **"0%" although none is empty** — 178 matters is 0.013%. | **Fixed** — `<0.1%` below the rounding floor, one decimal elsewhere. |
| F-18 | all | Titles clipped hard against the right frame at 630 px. | **Fixed** — title block width is container minus 14 px. |

**What changed by request rather than by defect:** Chart 5's bars now carry
percentages, matching its title's claim, with counts moved to the tooltip
(Rule 4.4 names the tooltip as the home for full precision, and the share was
already a column in the certified measure). Chart 3's labels are uniformly two
lines — act, then issue-joined group in parentheses — read from the dimension's
separate `description` and `group` columns. All 21 dispositions were kept: two
are already named "other" (codes 14 and 17), so a third synthetic "other" for
the tail would mislead rather than tidy.

### The tooltip decision, recorded so it is not re-derived

All five charts gained a tooltip. **This does not move the artifact to
Checklist B.** That list governs "interactive pages, filtered views, and any
artifact whose finding belongs to the reader" — every finding here is fixed in
a title and a tooltip moves none of them. Rule 5.5 governs tooltips *inside*
Checklist A, and Rule 4.4 names the tooltip as the home for full precision.

Two conditions, both met: the tooltip is **absent below 769 px**, because
CHART-REVIEW 5.5 fails a hover-following tooltip at ≤768 px and the drop order
makes it the first thing to go; and the provenance strip **stays at three
segments**, because Rule 4.4's fourth segment is required only where a control
changes what is shown, and this changes nothing. Styling is the theme's own
`tooltip` block — nothing invented.

Two figures were **typed** in a first draft of the page — the empty-description
share and the substring-match inflation. Both were replaced with values
computed at build time from committed artifacts (`fact_docket_event.jsonl` and
the response cache). K2 does not distinguish between a wrong number and a right
number nobody can re-derive.

---

### Third round — Aaron's read on a phone and a narrow desktop, 2026-08-29

Two reports, both reproduced before anything was changed. The second one
turned out to be three defects wearing one coat.

**F-19 · Chart 1 value labels drawn over their own bars.** Reported at ~465 px.
Reproduced exactly. Cause: leftward bars used `position: 'top'`, and an
ECharts label position anchors to the **data point**, which sits at the row's
vertical centre — not to the top of the rect. With `distance: 7` and a bar
half-height near 26 px, "7 px above the point" is 19 px *inside* the bar. The
rightward labels were never affected, which is why `+1062` and the three `0`s
always looked right and every negative value did not. **Fixed:** the position
is now `right`/`left` at every width — always outside the far end.

**F-20 · The axis padding was solved once, and reserving room is a fixed-point
problem.** Fixing F-19 moved the collision rather than ending it: at 320 px
`-742.3` then overlapped the *category* label. Padding the axis widens its
range, which shrinks pixels-per-unit, which shrinks the gap the padding just
bought. Solving `p·plotPx ≥ K·(R + 2p)` for `p` closes the loop.
**Fixed**, and it exposed F-21 underneath.

**F-21 · `plotPx` was estimated, and the estimate was 42% wrong.** Measured
against the real ECharts grid rect at four widths:

| viewport | host | real grid | old estimate |
|---|---:|---:|---:|
| 320 | 254 | **103** | 146 |
| 390 | 324 | **173** | 195 |
| 465 | 399 | **229** | 247 |
| 1040 | 974 | **667** | 680 |

Because the padding is proportional to `1/plotPx`, an over-estimated plot
**under-reserves** room. This was the original cause of F-19's whole class,
and no amount of position tuning would have reached it. **Fixed:** the
estimate now matches the measured rect.

**The 320 px case is geometrically impossible, and is handled by dropping the
label rather than by pretending.** A label needs ~57 px at each end of a
**103 px** plot. `2K > plotPx`, so no padding value exists. The usual
waterfall answer — put the label inside the bar — is **not available here**:
paper on madrona measures **4.31:1** and 12 px text needs 4.5:1 (paper on
evergreen passes at 5.18:1, but a rule that works for one hue and not the
other is not a rule). So below the fit threshold the value labels are dropped
per Rule 5.5's drop order, the bars keep true scale, and the note under the
chart says where the numbers went. Labels are present at 390 px and above.

**F-22 · The tooltip gate read the width instead of the pointer.** Reported as
"no hover popups on mobile"; the same gate also removed them from a *narrow
desktop window*, which has a mouse. CHART-REVIEW 5.5 fails a **hover-following**
tooltip at ≤768 px, and the reason is touch — there is no hover, and a readout
that chases the finger covers the mark it describes. Width was a proxy for
touch, and a bad one. **Fixed:** the gate is now
`(hover: hover) and (pointer: fine)`. A fine pointer keeps the hover tooltip at
every width; everything else gets the same readout **on tap, anchored to the
top of the plot**, which is not hover-following and does not engage 5.5.

Verified on an emulated touch context (`has_touch`, coarse pointer), not on a
narrow window: all five charts return `triggerOn: 'click'` with the anchored
position function, and the readout renders at top + 4 px inside the host. On a
mouse at 465 px and 1040 px it stays `mousemove|mouseout`. **465 px now has a
readout where the old gate gave it none.**

The provenance strip stays at **three** segments — 4.4's fourth is required
only where a control changes what is shown, and a readout changes nothing.
K5 re-checked at 320, 390 and 465: `[3, 3, 3, 3, 3]`.

### K6 — run, at last, and what running it showed

**K6 is an `INVARIANT` in both checklists and this module had never satisfied
it.** It requires the review to run *"at the narrowest width, the design width,
and ±1 px either side of every declared breakpoint."* `render_charts.py`
rendered 1040 and 320, and the module passed a Rule 7.4 reading panel on that
basis. The check that would have caught this build's most expensive defect
already existed and was simply not executed.

**The defect it would have caught.** Chart 1 drew every negative value label
inside its own bar, because a narrow-only branch anchored the label to the row
centre instead of the bar's end. That branch exists below a host width of 560.
Rendering either side of the crossing puts the two states side by side:

| viewport | `narrow` | the four negative labels |
|---|---|---|
| 625 | true | drawn **inside** their bars |
| 626 | false | drawn outside, clear |

Demonstrated by reintroducing the defect deliberately and rendering both.

**±1 px of the breakpoint is not ±1 px of the viewport, and assuming it was
cost a round.** `layout()` branches on `host.clientWidth`; the host is about
66 px narrower than the viewport for a full-width chart. The obvious ladder —
559 and 561 against a declared breakpoint of 560 — leaves `narrow` **true on
both sides**. Two renders that straddle nothing, and a ladder that looks correct
while testing the same branch twice. `render_charts.py` now binary-searches, per
chart and per breakpoint, for the viewport at which that chart's host actually
crosses, and renders the pair either side of the crossing.

**The ladder is derived, never typed.** `docs/assets/page.js` declares
`CASCADIA_BREAKPOINTS` once and `layout()` reads it; the harness reads it off
`window`. A breakpoint that is used must be declared, and a declared breakpoint
is rendered whether or not anyone remembers it. Typing the widths in the harness
is what let K6 go unrun.

**Run of 2026-08-29:**

```
K6 ladder derived from declared breakpoints 560, 900
  c1..c5 cross host 560 px between viewport 625 and 626
  c1..c5 cross host 900 px between viewport 965 and 966
  widths: 320, 625, 626, 965, 966, 1040
  strip segments [3,3,3,3,3] at every width
  no horizontal overflow at any width
```

Two checks now run in the same pass, both added because this build found them
the hard way. The **real ECharts grid rect** is printed per chart per width —
`page.js` estimated it at 146 px where the truth was 103, and since axis padding
goes as `1/plotPx` an over-estimate *under*-reserves label room, which was the
root of the whole label class. And **horizontal overflow** is asserted at every
width, exiting non-zero: Rule 5.3 adopts WCAG 1.4.10 and nothing had ever tested
it, which is how a sibling page shipped 542 px wide at a 390 px viewport
underneath a green accessibility check.

### Interaction is outside what the panel can see

Every tooltip defect in this build — four rounds of them — was invisible to the
Rule 7.4 panel by construction, because the panel reads **static renders**. No
number of additional seats would have changed that. `src/test_touch_readout.py`
covers the gap: it scrolls each chart's container top above the fold and asserts
the readout lands inside the **viewport**, and it is forbidden from calling
`scrollIntoView` — which is precisely what made three earlier rounds of tests
pass against a page that was broken on a real phone.

## 3 · Renders handed to the panel

**Twelve files: five charts at two widths, plus a full-page render at each.**

| Viewport | Chart element | Why | Files |
|---|---|---|---|
| **1040 px** | **1000 CSS px** | design width | `docs/renders/{c1..c5,page}-1040.png` |
| **320 px** | **280 CSS px** | Rule 5.3 / WCAG 1.4.10 reflow floor | `docs/renders/{c1..c5,page}-320.png` |

**The filename is the viewport width, not the chart's width, and the panel is
given both numbers.** The page's own margins take the element narrower than the
viewport, so the 320 px set exercises the charts at **280 CSS px — below the
320 px floor `CASCADIA.minCanvasPx` declares.** That is a harder test than the
standard asks for and the charts are read at it, but it is stated rather than
left for a seat to infer from a filename.

CHART-REVIEW v2.5 makes "design width only" a FAIL condition on check 7.4, so
both sets exist and both are handed over. Rendered at `deviceScaleFactor: 2`,
so image pixels are twice the CSS values above.

**Two further widths — 630 px and 768 px — are rendered for verification and
are not part of the panel set.** 630 px is where F-12 and F-18 were found: a
width that fell between the two deliverable renders and so was never looked at.
`src/render_charts.py <width> --out <dir>` produces them on demand.

**The un-panelled baseline is frozen** at `governance/panel-specimen/2026-08-28-v1/`
and tagged `panel-specimen-v1`, so the charts as they stood before this round
still exist for a generic-vs-tuned panel comparison.

## 4 · The Rule 7.4 reading panel — RUN 2026-08-28

**Status: complete. Roster, returns, disposition and metrics are in section 0
above. 16 findings, 10 defects, all 10 fixed; 6 rejected with reasons.**

*This section previously read "NOT YET RUN" and is kept, amended, rather than
deleted — the record should show that publication was gated on the panel and
that the gate was actually closed before it opened.*

| Field | Value |
|---|---|
| Roster | 3 domain seats + 1 visualization seat, cast from the Rule 0.1 decision |
| Nature | **simulated** |
| Widths given to seats | 1040 px and 320 px viewports (chart elements 1000 and 280 CSS px) — both sets, per CHART-REVIEW v2.5 |
| Findings | 16 · defects 10 · rejected 6 · multi-seat defects 4 |
| Disposition | all 10 defects fixed; 6 rejected with stated reasons |
| Metrics | D = 2.00 · N = 0.80 · R = 0.38 |
| Machine-readable | `governance/panel/findings.json` |
| Author's pre-panel notes | `governance/pre-panel-notes.md`, written before spawning |

**The publication gate is now satisfied.** Rule 7.4 requires the blind
multi-seat read *before* charts ship. It ran on 2026-08-28, against the
un-panelled specimen frozen at `panel-specimen-v1`, and its ten defects were
fixed before anything went near the site.

**A panel that returns nothing is recorded as "no findings" and never as a
pass.** This one returned sixteen, so that clause did not arise — but it is
restated here because the next panel is where it will matter.
