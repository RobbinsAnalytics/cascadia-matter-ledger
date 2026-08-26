# Source register — Cascadia Matter Ledger

*Stage 1 artifact. Owner: Aaron Robbins. Established 2026-08-26.*

This file is the authoritative record of **what was pulled, from where, when,
and what it hashes to.** Nothing downstream re-downloads. `src/validate_freeze.py`
re-computes the hash below and fails the build if it has moved.

---

## S-01 · FJC Integrated Database — civil, statistical year 1988 forward

| | |
|---|---|
| **Publisher** | Federal Judicial Center, under working arrangement with the Administrative Office of the U.S. Courts |
| **Dataset page** | `https://www.fjc.gov/research/idb/civil-cases-filed-terminated-and-pending-sy-1988-present` |
| **File retrieved** | `https://www.fjc.gov/sites/default/files/idb/textfiles/cv88on.zip` |
| **Retrieved** | 2026-08-26 |
| **Publisher `Last-Modified`** | 2026-08-26T15:28:04Z |
| **Bytes** | 329,665,474 |
| **SHA-256** | `74405231a9a3c246c7090d471a1525924fa5afb513ff22b4dc0f4babbac7223d` |
| **Member** | `cv88on.txt` — 2,009,227,701 bytes uncompressed, tab-delimited, 46 columns |
| **Rows** | 10,960,173 |
| **Licence** | US federal government work, published for public access. Not redistributed by this repo. |

**Not committed to git, deliberately.** 314 MB compressed / 2.0 GB expanded is
outside what git should hold. The freeze is asserted by hash, not by tracking
the bytes: `data/raw/cv88on.zip.sha256` and this file are the committed record.
Everything derived from the snapshot — `data/reference/`, `data/conformed/` —
is committed and is small. This is the module's one deliberate departure from
the house pattern, which commits `data/raw/` outright.

**The publisher updates this file quarterly and in place.** The URL is not
versioned; a later pull returns different bytes under the same name. That is
precisely why the hash is the freeze and why nothing re-downloads.

## S-02 · Civil codebook

| | |
|---|---|
| **File** | `https://www.fjc.gov/sites/default/files/idb/codebooks/Civil%20Codebook%201988%20Forward%2010252023.pdf` |
| **Publisher revision** | 2023-10-25, per the filename |
| **Retrieved** | 2026-08-26 |
| **Pages** | 17 |
| **Coverage** | All 46 columns of `cv88on.txt` are documented. Verified by cross-check, not assumed. |

This codebook is the source of the conformed dimensions in Stage 2. Code
meanings are loaded **from** it; they are never written as `CASE WHEN` blocks
inside a query.

## S-03 · IDB Research Guide

| | |
|---|---|
| **File** | `https://www.fjc.gov/sites/default/files/IDB-Research-Guide.pdf` |
| **Retrieved** | 2026-08-26 |
| **Pages** | 4 |

Source of the collection-process facts that govern how this data may honestly
be read — quarterly refresh, in-place record replacement, and the redaction
policy. See F-03.

## S-04 · CourtListener REST API v4 — *Stage 5, not yet used*

| | |
|---|---|
| **Root** | `https://www.courtlistener.com/api/rest/v4/` — reachable, HTTP 200 |
| **Authentication** | **Required.** Every endpoint this module needs returns HTTP 401 unauthenticated. `/search/` is the sole exception. |
| **Rate limit** | 5 requests/minute, 50/hour, 125/day for default authenticated users, rolling window, all three concurrent |
| **Token** | Not yet obtained. **This is a live blocker on Stage 5.** |

---

## Findings established at acquisition

**F-01 · The civil file carries party names.** `PLT` ("first listed plaintiff")
and `DEF` ("first listed defendant") are documented in the codebook and
populated on **100% of 10,960,173 rows**. The build brief recorded the opposite
as a recollection. It was wrong, and the consequence is that the subject-matter
exclusion is a **pipeline filter with an owner**, not a precaution. See
`governance/subject-matter-filter.md`.

Note the asymmetry, which is itself governance-relevant: the FJC redacts the
names of *criminal* defendants and of *judges* under Judicial Conference
policy, and redacts neither party in civil cases. The redaction is a policy
choice about people, not a de-identification of the dataset.

**F-02 · Pending cases carry a sentinel termination date, and it is not null.**
479,405 rows have `STATUSCD = 'S'` (pending). Every one of them carries
`TERMDATE = 01/01/1900`, `TAPEYEAR = 2099`, `DISP = -8` and `PROCPROG = -8`.

A filing-to-termination duration computed against the raw file therefore
returns a **negative interval of several decades** for 4.4% of all rows — for
example a case filed 2001-10-29 "terminating" on 1900-01-01. The value is not
missing, so it does not drop out of an average; it is a well-formed date that
silently poisons every duration measure computed over it.

`-8` is the file's documented missing marker, and `01/01/1900` and `2099` are
undocumented sentinels that appear nowhere in the codebook. This is the
module's central worked example of *missing-is-meaningful*, and it is the
Stage 6 proof: the ungoverned answer is not slightly wrong, it is wrong by
sign.

**F-03 · The snapshot is a status snapshot, not an event log.** The FJC
replaces a case's record on each quarterly update rather than appending to it,
and after a fiscal year closes the record stops updating altogether. A case's
row reflects its state as of the most recent refresh, not its history. Any
measure phrased as "how often did X happen over the life of the case" is
**not** answerable from this source, and saying so is part of the model.

**F-04 · `STATUSCD` has an undocumented third state.** 7,297,049 rows are `'L'`,
479,405 are `'S'`, and **3,183,081 are blank** — 29% of the file. The blanks
concentrate in the earlier statistical years. The codebook documents no blank
state. Quantifying where it starts and stops is Stage 2 work and is a candidate
effective-dated boundary.

**F-05 · `FILEDATE` runs from 1901 to 2026.** The lower bound is not credible
as a federal civil filing date in a 1988-forward file and is a data-quality
artifact, not a long-running case. It is recorded here so that a later session
does not rediscover it as a defect in this module's own code.
