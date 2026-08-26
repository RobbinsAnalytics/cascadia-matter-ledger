# Certified measure register

*Stage 4 artifact. Owner of every measure below: **Aaron Robbins**.*
*Established 2026-08-26. Snapshot as-of 2026-08-26.*

Every measure carries a written definition, a named owner, lineage to source
fields, and a stated limit. A figure that appears in any rendered output and is
not defined here is not certified and must not be published.

**Population.** All measures are computed over `fact_matter`: 1,405,046 status
records covering 1,403,097 contract and commercial matters in the US district
courts, statistical years 1988 to 2026, after the subject-matter control in
`subject-matter-filter.md` and the quarantine in `docket-to-matter.md` R-04.

**Independent validation.** `src/validate_measures.py` re-derives every
published cell from the frozen file down a separately written path — the
party-name normalisation is implemented in SQL there and in Python in the build,
so a bug in one does not reproduce in the other. **Nothing is published unless
that script exits zero.**

---

## The two words that do the work

Two qualifiers appear in nearly every definition. They are not boilerplate.

**"Closed"** means `is_closed`, which is asserted from `STATUSCD` for
statistical year 2001 onward and from a non-sentinel `TERMDATE` before that.
It is never inferred from the presence of a termination date alone, because
479,405 pending records in the source carry `TERMDATE = 01/01/1900`.

**"Latest record"** means `is_latest_record`. A matter reopened after
termination produces a second status record with a later disposition; 1,949 of
them exist in this slice. Measures that answer *how did this matter end* count
each matter once, at its latest record.

---

## M-01 · Time to termination

> **Definition.** For a closed matter, at its latest record, the number of
> calendar days from `FILEDATE` to `TERMDATE`. Reported as the median, with the
> 25th and 75th percentiles, grouped by nature of suit and separately by court.

| | |
|---|---|
| **Owner** | Aaron Robbins |
| **Outputs** | `data/conformed/m01_time_to_termination_by_nos.csv`, `..._by_court.csv` |
| **Lineage** | `FILEDATE`, `TERMDATE`, `STATUSCD`, `NOS`, `CIRCUIT`, `DISTRICT` |
| **Population** | `is_closed AND is_latest_record AND days_to_termination IS NOT NULL` |
| **Statistic** | Median, not mean. Duration distributions in litigation are heavily right-skewed and a mean is dragged by a small number of decade-long matters. |

**Limits.**
- This is **court-docket duration, not matter duration.** The department's
  clock starts before filing and stops after termination. See
  `docket-to-matter.md` L-05. The figure is a lower bound.
- Courts are reported only where at least 1,000 closed matters exist, so that a
  median is not published over a handful of cases.
- A reopened matter's duration is measured to its **latest** termination, so it
  includes the dormant interval between closure and reopening.

---

## M-02 · Disposition mix

> **Definition.** The count and percentage of closed matters, at their latest
> record, by `DISP` — the manner in which the court disposed of the case.

| | |
|---|---|
| **Owner** | Aaron Robbins |
| **Output** | `data/conformed/m02_disposition_mix.csv` |
| **Lineage** | `DISP`, `STATUSCD`, decoded through `dim_disp` |
| **Population** | `is_closed AND is_latest_record` |

**Limits.**
- `DISP` is the *court's* characterisation. "Settled" (code 13) means the court
  recorded a settlement, not that the department considers the matter resolved
  on favourable terms.
- The three documented groups — transfers and remands, dismissals, judgments —
  are preserved in the dimension and must not be collapsed. A transfer is not
  an outcome; it is the same matter continuing elsewhere, and it is why
  `docket-to-matter.md` L-01 exists.

---

## M-03 · Procedural progress at termination

> **Definition.** The count, percentage and median duration of closed matters,
> at their latest record, by `PROCPROG` — the point the case had reached when
> it was disposed of — **qualified by its issue-joined group.**

| | |
|---|---|
| **Owner** | Aaron Robbins |
| **Output** | `data/conformed/m03_procedural_progress.csv` |
| **Lineage** | `PROCPROG`, `FILEDATE`, `TERMDATE`, decoded through `dim_procprog` |
| **Population** | `is_closed AND is_latest_record` |

**The group qualifier is mandatory and is the reason this measure exists.**
`PROCPROG` codes 1 and 3 both read "no court action" in the codebook's code
list. They are not the same state: code 1 is before issue was joined, code 3 is
after. The codebook carries the distinction as a header above the list, not in
the code descriptions, so a dimension built from code and description alone
merges 379,357 matters — 27.7% of the slice — into one ambiguous label.
`dim_procprog` therefore carries a `group` column and a
`qualified_description`, and this measure reports the qualified form.

**Limits.**
- "Issue joined" is defined by the publisher as the date the last defendant's
  answer was filed before the first proceeding. In multi-defendant matters the
  publisher's own note acknowledges this is imprecise.
- Progress is recorded at termination only. A matter's path there is not
  observable — see `docket-to-matter.md` L-06.

---

## M-04 · Filing volume trend by nature of suit

> **Definition.** The count of distinct matters whose `FILEDATE` falls in each
> calendar year, by nature of suit. Counts matters, not status records.

| | |
|---|---|
| **Owner** | Aaron Robbins |
| **Output** | `data/conformed/m04_filing_volume_by_year.csv` |
| **Lineage** | `FILEDATE`, `NOS` |
| **Population** | Filing years 1988–2026 |

**Limits.**
- **The tails are not comparable to the middle and must not be read as trend.**
  The file covers statistical years 1988 forward, so a matter filed in 1985 and
  terminated in 1990 appears while its 1985 peers that terminated in 1986 do
  not. Filing years before 1988 are censored on the left, and 2026 is a partial
  year censored on the right.
- Counted by calendar year of filing, not by the publisher's statistical year,
  which changed definition in 1992. Mixing the two is a known way to produce a
  spurious spike.

---

## M-05 · Open inventory and aging

> **Definition.** The count and percentage of matters not closed as at the
> snapshot's as-of date, banded by days elapsed since `FILEDATE`.

| | |
|---|---|
| **Owner** | Aaron Robbins |
| **Output** | `data/conformed/m05_open_inventory_aging.csv` |
| **Lineage** | `FILEDATE`, `STATUSCD` |
| **Population** | `NOT is_closed AND is_latest_record` |
| **As-of** | 2026-08-26, the snapshot's retrieval date — **not** the date the script runs. Otherwise the figure drifts every time anyone re-runs it. |

**Limits.**
- Open inventory is only observable from statistical year 2001, when `STATUSCD`
  began to be captured. Before that a pending case is simply absent from the
  file. This measure has no history before 2001 and must never be plotted as
  though it does.
- Age is measured from filing, not from the department's matter-open date.

---

## Measures deliberately not certified

**Amount demanded and amount recovered.** `DEMANDED` and `AMTREC` are present
and are tempting. They are not certified, for a reason the codebook states
outright: amounts are recorded in thousands, values under $500 appear as `1`,
values over $10,000 appear as `9999`, and *"in the past, courts have not always
reported this field in thousands of dollars, therefore data may not be
accurate."* A publisher's own accuracy warning is a reason to leave a field
alone, not a caveat to put under a chart.

**Anything resembling legal spend.** There is no cost data in this source. See
`docket-to-matter.md` L-03.
