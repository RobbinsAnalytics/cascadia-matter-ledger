# The subject-matter exclusion rule

*Section 6 control. **Mandatory.** Owner: Aaron Robbins.*
*Established 2026-08-26, on the day the underlying assumption was found false.*

---

## The control objective

> **Nothing this module produces may read as an assessment of the litigation
> exposure of T-Mobile, of any predecessor or affiliate of T-Mobile, or of any
> other telecommunications carrier.**

This is a hard constraint on the artifact, not a stylistic preference. The
measures in this module are domain-agnostic, so satisfying it costs no
analytical content.

## Why it became a control rather than a precaution

The build brief recorded, from recollection, that the FJC civil file holds no
party names. **It does.** `PLT` and `DEF` are documented in the codebook and
populated on 100% of 10,960,173 rows (`source-register.md` F-01). A dataset
that names parties is a dataset in which an exclusion has to be *implemented*
and *evidenced*, not merely intended.

---

## Three layers, in order of strength

The layers are deliberately ordered weakest-last. The design carries the
control; the name match is a belt on top of braces, and its limits are stated
because a heuristic presented as a guarantee is worse than no heuristic.

### Layer 0 — design. *Structural. No exceptions possible.*

**No measure in this module is cut by party, and nothing is published at party
grain.** Every figure is an aggregate over roughly 1.4 million contract and
commercial cases spanning 1988–2026, reported by nature of suit, by court, by
disposition and by year.

There is no output shape in which a single organisation's exposure could be
read, because no output has an organisation in it. This is the layer that
actually satisfies the control objective, and it is enforced by the build:
`fact_matter` carries no party column downstream of the filter.

### Layer 1 — scope. *Structural. Auditable by code list.*

The model covers **contract and commercial disputes only**:

| NOS | Description | NOS | Description |
|---|---|---|---|
| 110 | Insurance | 153 | Recovery of Overpayments of Vet Benefits |
| 120 | Marine Contract Actions | 160 | Stockholder's Suits |
| 130 | Miller Act | 190 | Other Contract Actions |
| 140 | Negotiable Instruments | 195 | Contract Product Liability |
| 150 | Overpayments & Enforcement of Judgments | 196 | Franchise |
| 151 | Overpayments under the Medicare Act | | |
| 152 | Recovery of Defaulted Student Loans | | |

Chosen because commercial disputes are the canonical corporate legal-operations
workload and the largest single driver of outside-counsel spend — the module is
*about* the work a legal department manages. Patent and trademark
(NOS 820–840) are **deliberately excluded**: carriers are structurally
over-represented there, and an IP slice would make the exclusion harder to
defend for no analytical gain.

### Layer 2 — name exclusion. *Heuristic. Measured, and its residual published.*

Any case whose `PLT` or `DEF` matches the exclusion list in
`data/reference/excluded_parties.csv` is dropped from `fact_matter` before any
measure is computed. Matching is case-insensitive on a normalised form
(punctuation and corporate suffixes stripped), **on word boundaries**, and
**at docket level**. Both of those qualifications were added after the first
build, and each fixed a real defect found by running it:

- **Word boundaries, not substrings.** A raw substring match put the token
  `t mobile` inside `BIG RIVER DISCOUN|T MOBILE` and `spectrum` inside
  `SPECTRUM INVESTMENT`, excluding cases with no connection to any carrier.
  755 of the original 8,826 matches were false positives of this kind.
- **Docket level, not row level.** The same docket carries the carrier's name
  spelled differently across its records — `CONTI CABLEVISION N E`,
  `CONTI CABELISION ON N E` (the source's own typo) and
  `CONTINENTAL CABLE, ET AL` are three records of one case. A row-level filter
  dropped one and kept another; 14 cases survived that way. Excluding the whole
  docket closes it.

**Measured on the 2026-08-26 build:** 1,413,138 records in scope, **8,071
matched the exclusion list**, **8,092 excluded at docket level** — the 21-record
difference is over-exclusion caused by docket-number reuse, which is the safe
direction and is counted rather than hidden.

The list covers T-Mobile and its predecessors and affiliates — including
Sprint, Nextel, MetroPCS, VoiceStream, Omnipoint and Powertel — and the other
major US carriers and their operating entities, including the ones that
litigate under names that do not contain the brand, such as Cellco Partnership
(Verizon Wireless) and New Cingular Wireless (AT&T Mobility).

**Every run publishes how many rows this layer dropped.** A filter whose catch
count is never reported is a filter nobody has checked.

---

## What Layer 2 cannot do

Stated plainly, because a controls reader will ask and a systems reader will
already know:

1. **`PLT` and `DEF` are first-listed parties only.** A carrier appearing as
   the third defendant is invisible to the match. This is a property of the
   source, not of the implementation, and it cannot be engineered around.
2. **The fields are free text with no normalisation, and the source contains
   misspellings.** This is not a hypothetical: `CONTI CABELISION ON N E` is a
   real value in the frozen file, on a docket whose other records read
   `CONTI CABLEVISION N E`. Abbreviations, `d/b/a` forms and subsidiary names
   sharing no token with the parent evade the list in the same way.
   Docket-level exclusion recovers the cases where *some* record spells the
   name recognisably; it recovers nothing where *no* record does.
3. **Insurers and servicers are frequently the named party** in commercial
   disputes where the operating company is the real interest.
4. **The list is a point-in-time artifact.** Corporate names change; the list
   does not update itself.

**None of this defeats the control objective, because Layer 0 does not depend on
Layer 2.** Layer 2 exists so that the excluded parties are also absent from the
intermediate data a reviewer might inspect — not because the published figures
would otherwise be at risk.

---

## Assertions re-tested on every run

| # | Assertion | Evidence | On failure |
|---|---|---|---|
| SM-1 | `fact_matter` contains no party-name column | Schema check | Build fails, publishes nothing |
| SM-2 | Every `fact_matter` row has a nature of suit inside the Layer 1 list | Set difference is empty | Build fails |
| SM-3 | No `fact_matter` row's source record matched the exclusion list | Re-match against the frozen snapshot | Build fails |
| SM-4 | The Layer 2 drop count is published | Present in the run record | Run marked incomplete |

SM-3 is deliberately redundant with the filter itself. A control that is only
ever applied, never re-verified, cannot tell you the day it stops working.
