# Panel specimen — 2026-08-28-v1

**These five charts have never been panelled.** They are frozen here as the
un-panelled baseline for a later generic-vs-tuned reading-panel comparison.
Nothing in this directory is regenerated. Revisions to the live charts happen
in `docs/`, never here.

Twelve files: five charts at two widths, plus a full-page capture at each.

| | |
|---|---|
| Source commit | `2876c0a` — verified byte-identical, see `manifest.json` |
| Tag | `panel-specimen-v1` |
| Rendered | 2026-08-26 |
| Frozen | 2026-08-28 |
| Standard | `VIZ-PRINCIPLES.md` v2.7 · `CHART-REVIEW.md` v2.7 · Checklist A |

**The filename carries the viewport width, not the chart's.** Page margins take
the element narrower: `-1040` renders the chart at **1000 CSS px** and `-320` at
**280 CSS px** — below the 320 px floor the design system declares it supports.
Image pixels are twice the CSS width (`deviceScaleFactor: 2`).

A seat reading these should be given the chart-element width, not the filename.
