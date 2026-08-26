# The docket-to-matter mapping rule

*Stage 3 artifact. **Written before the code that implements it.***
*Owner: Aaron Robbins. Established 2026-08-26. Status: in force.*

---

## Why this document exists first

A docket is not a matter.

A **docket** is a court's record of a case: one caption, one court, one docket
number, opened when a complaint is filed and closed when the court disposes of
it. It exists because a court needs to administer a proceeding.

A **matter** is a legal department's internal unit of work: the thing that gets
opened, budgeted, staffed, billed against, reported on, and closed. It exists
because a department needs to manage its own effort.

These are related and they are not the same. Every measure in this module is
computed over court records and reported in the language of matters, and that
translation is the single largest assumption in the build. It is therefore
written down, owned, and bounded here — before any code performs it — rather
than left implicit in a join.

---

## R-01 · The mapping rule, in plain English

> **One IDB civil case record is treated as one matter-shaped entity of type
> *external litigation — federal civil*, identified by the composite key
> `CIRCUIT · DISTRICT · OFFICE · DOCKET`, opening on `FILEDATE` and closing on
> `TERMDATE` where `STATUSCD` indicates the case has terminated.**

Three clauses, each of which is a decision:

**R-01.a — the grain.** One row, one matter. Not one row per party, not one row
per docket entry. The IDB civil file is already case-level, so this preserves
the publisher's grain rather than inventing one.

**R-01.b — the identity.** *Amended 2026-08-26 after the first build failed its
own uniqueness assertion.* There are **three** grains here and conflating any
two of them produces a wrong number:

| Key | What it identifies | Unique? |
|---|---|---|
| `docket_key` = circuit·district·office·docket | The court's file | **No.** Docket numbers are reused for unrelated cases years apart. `5-41-4-8600763` is *Irving Trust v. Blanco* filed 1986 **and** *Drew Chemical v. Grana* filed 1988. |
| `matter_key` = `docket_key`·filing date | One dispute | Yes, at matter grain |
| `record_key` | One status record | Yes. This is the fact table's grain. |

`DOCKET` alone is never a key: it repeats across districts, across offices
within a district, and across unrelated cases within one office. Joining on it
produces silent fan-out.

**A matter can hold more than one record.** 1,949 of the 1,405,046 records in
this slice are second or third status records for a matter that was terminated
and later reopened — a different disposition, a later termination date, the
same dispute. Both records are true; they describe different points in the
matter's life. The fact table keeps all of them and flags the latest with
`is_latest_record`. Any measure that answers *"how did this matter end"* uses
the latest record and says so in its definition; any measure that counts
activity uses all records and says that instead.

This was not designed in. The first build asserted one row per matter, failed
on 1,947 keys, and the assertion was right and the rule was wrong.

**R-01.c — the clock.** A matter's open date is the court's filing date and its
close date is the court's termination date. **This is the court's clock, not the
department's** — see L-05.

## R-02 · Matter type is asserted, not observed

Every entity produced by R-01 is typed *external litigation — federal civil*.
The source contains no other kind of work, so the type carries no information
within this model. It is recorded explicitly so that a reader never mistakes
this module's coverage for a department's whole portfolio, and so that a later
extension adding a second matter type has somewhere to put it.

## R-03 · Termination is asserted from status, never from the date

*Amended 2026-08-26, before first implementation. The original clause is kept
below because the reason it was wrong is the module's own argument turned on
itself.*

**As originally written:** a matter is closed if and only if `STATUSCD` says so,
and `TERMDATE` is never consulted to decide whether a case has ended.

That clause exists because of a specific defect in the source: all 479,405
pending records carry `TERMDATE = 01/01/1900`, a well-formed date that is not a
termination. Any rule that infers closure from the presence of a termination
date closes half a million open matters and computes negative durations for
them. See `governance/source-register.md` F-02.

**Why it had to be amended.** `STATUSCD` did not exist before statistical year
2001. It is empty on 3,183,081 rows — 29% of the file — and every one of those
records is in fact a terminated case carrying a real termination date. A rule
that trusts `STATUSCD` alone reports 3.18 million closed matters as open.

**The rule, as it now stands — and it is effective-dated, like the dimensions:**

| Statistical year | Closure test |
|---|---|
| 2001 and later | Closed iff `STATUSCD = 'L'`. Open iff `STATUSCD = 'S'`. |
| 2000 and earlier | `STATUSCD` did not exist. Closed iff `TERMDATE` is a real date — that is, present and not the `01/01/1900` sentinel. |

Verified against the snapshot: no record with `STATUSCD` empty carries the
sentinel date, and no record with `STATUSCD = 'L'` does either. The two eras do
not overlap and the test is unambiguous in each.

**This is worth saying out loud.** The module argues that codes change meaning
across years and that flattening them loses information. Its own closure rule
turned out to be the first casualty. The rule is effective-dated because the
field is, and it was caught by checking the data against the codebook rather
than by writing the obvious clause and shipping it.

## R-04 · Malformed source records are quarantined, never repaired

638 of 10,960,173 records contain an embedded tab character inside the `DEF`
field. The delimiter appears inside a value, so every field to the right of
`DEF` shifts one or two positions left — corrupting `TERMDATE`, `DISP`,
`PROCPROG`, `STATUSCD` and `TAPEYEAR` on those rows. A load that splits on tabs
and asks no further questions accepts all 638 silently and reports disposition
codes that are actually fragments of dates.

Such records are **written to a quarantine table with the reason, counted, and
excluded from `fact_matter`.** They are never guessed at. The count is
published on every run: a quarantine nobody reports is a delete.

---

## What the mapping loses

A rule that does not state its losses is an assumption wearing a rule's
clothing. These are the losses, in descending order of how much they matter.

**L-01 · A matter may span several dockets, and this model will count it more
than once.** Multidistrict litigation consolidates many filings under one MDL
number; a transferred case exists as a record in both the losing and the
receiving district. The department experiences one matter; the court system
records several.
*Partly observable.* `MDLDOCK`, `TRANSDOC` and `TRANSORG` are present in the
file, so the size of this loss is **measured and reported** rather than merely
conceded. The measurement is published with the metric register. Consolidation
that happens without an MDL number remains invisible.

**L-02 · A matter may exist with no docket at all, and this model cannot see
it.** Pre-suit demands, negotiated resolutions, mediation, arbitration,
regulatory inquiries and internal investigations are legal work that never
reaches a federal civil docket. For most corporate legal departments this is
the *majority* of the portfolio. Nothing in this module estimates it, and no
figure here should be read as a share of total legal work.

**L-03 · Cost is entirely absent.** There is no spend, no timekeeper, no rate,
no vendor and no budget in this source. Every cost statement this module makes
is an inference from procedural distance travelled, and is labelled as such.
`DEMANDED` and `AMTREC` are amounts in controversy and amounts recovered — they
are case values, not legal costs, and are never presented as spend.

**L-04 · Party role is not reliably recoverable.** `PLT` and `DEF` hold the
*first-listed* plaintiff and defendant only. In a multi-party case the model
cannot establish which side a given organisation is on, or whether it is
present at all. No measure in this module is cut by party role.

**L-05 · The court's clock is not the department's clock.** A department opens
a matter when the dispute arrives — a demand letter, a preservation notice —
and closes it after the court is finished, when the final invoice is paid.
`FILEDATE` to `TERMDATE` is therefore a **lower bound** on matter duration, and
every duration measure in this module is named and defined as court-docket
duration rather than matter duration.

**L-06 · The record is a status snapshot, not an event log.** The publisher
replaces a case's record on each quarterly refresh and stops updating it once
the fiscal year closes. The row states what was true at the last refresh, not
what happened along the way. Questions of the form *"how many times did X
happen during this matter"* are not answerable from this source.

**L-07 · One filing is not one dispute.** Claims are severed, consolidated,
amended and refiled. The court's docket count and the department's dispute
count diverge, and this model reports the former.

---

## How this rule is enforced

| Assertion | Evidence | Exception behaviour |
|---|---|---|
| The composite key is unique at matter grain | Row count equals distinct-key count in `fact_matter` | Build fails; duplicates written to the run record |
| No matter closes without `STATUSCD` saying so | Count of closed matters equals count of terminated `STATUSCD` values | Build fails |
| No matter has a negative duration | Min duration over closed matters is >= 0 | Build fails |
| The size of L-01 is stated, not assumed | Multi-docket row counts published in the metric register | Figure is republished each run |

These are re-asserted on **every** pipeline run, not once at build time. A run
that cannot assert them publishes the failure rather than the figures.

## Changing this rule

Any change to R-01, R-02 or R-03 changes what every published figure means and
is a versioned amendment to this document with a dated reason, not an edit. The
owner named at the top signs it.
