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

## 4 · The Rule 7.4 reading panel — NOT YET RUN

**Status: outstanding. This is not a pass and must not be recorded as one.**

The panel reads rendered charts, not a deployed site, so it can run against the
renders above without a rebuild. Per the frontend brief §6 the panel is run
from Cowork with the `cascadia-reading-panel` skill.

When it runs, this section records: the roster, the panel's **nature**
(`human` or `simulated`), **the widths each seat was given**, the findings, and
the disposition of each. **A panel that returns nothing is recorded as "no
findings" — never as a pass.**

| Field | Value |
|---|---|
| Roster | — |
| Nature | — |
| Widths given to seats | — |
| Findings | — |
| Disposition | — |

**Publication is gated on this.** Rule 7.4 requires the blind multi-seat read
*before* charts ship; publishing first and reviewing after would invert it.
