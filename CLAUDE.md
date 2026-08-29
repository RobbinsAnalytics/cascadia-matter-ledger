# Cascadia Matter Ledger — what an agent needs to know

A governed dimensional model of the **public federal civil docket**, with
legal-operations certified measures on top. Data layer only so far. It
publishes nothing yet and has no git remote.

**The estate's session rules — surfaces, guards, and the traps that have each
cost a session — are at
`C:\Projects\cascadia-standards\governance\SESSION-RULES.md`.** Read §1–§7 and
stop at the line. What gets published is governed by `PRINCIPLES.md` in the
same directory.

## The hard constraint, before anything else

**No telecommunications carrier may be the subject of analysis here, and
nothing produced may read as an assessment of any identified party's
litigation exposure.** The source names
parties — `PLT` and `DEF` are populated on every row — so this is an
implemented filter, not an intention. The rule, its three layers and its
measured limits are in `governance/subject-matter-filter.md`. Do not add a
measure cut by party, and do not publish anything at party grain.

## The freeze

**The data is frozen as-of 2026-08-26 and that date is a claim made out loud.**
`governance/source-register.md` holds the URLs, the retrieval date and the
SHA-256. Nothing re-downloads: `src/build_conformed.py` verifies the hash and
exits non-zero if it moved. **Refreshing is a deliberate act, never a side
effect** (PRINCIPLES rule 1).

**This module departs from rule 1's mechanism, deliberately and on the record.**
Rule 1 says commit the raw response. The snapshot is a 314 MB zip expanding to
2.0 GB, so `data/raw/cv88on.zip` and the files derived from it are gitignored
and **the freeze is asserted by hash instead**. The reason is written into
`.gitignore` and the source register. A fresh clone therefore has no snapshot —
re-fetch it from the recorded URL and check it against the recorded hash. That
is a verified restore, not a re-pull.

## Four properties of the source that have each already broken a build

The FJC documents none of these.

1. **The file is not UTF-8.** A UTF-8 read aborts partway through statistical
   year 2003. `build_conformed.py` transcodes once, counting what it changed.
2. **There is no quoting convention and party names contain bare quote
   characters.** At a CSV reader's defaults, 638 rows have their fields merged
   and every value right of `DEF` shifts. Read with `quote='' escape=''`.
   Those 638 rows are quarantined under R-04 and are never repaired.
3. **Pending cases carry `TERMDATE = 01/01/1900`, not null.** A duration
   computed against the raw file is negative by decades for 479,405 rows, and
   the value is well-formed so it does not drop out of an average.
4. **`STATUSCD` does not exist before statistical year 2001** and is empty on
   29% of the file — all of them terminated cases. Trusting it alone reports
   3.18 million closed matters as open. The closure rule is effective-dated;
   see `governance/docket-to-matter.md` R-03.

**A docket is not a matter, and the docket key is not unique.** Docket numbers
are reused for unrelated cases years apart, and a reopened matter produces a
second status record. Three grains exist and are named in
`docket-to-matter.md` R-01.b. Never join on `DOCKET`.

## Committing

**Stage by name — never the two blanket forms.** They are denied in
`.claude/settings.json`, and that block does **not** bind under
`bypassPermissions`. What binds is
`.claude/hooks/no_blanket_add_or_force_push.py`, a `PreToolUse` hook.

**Line-ending churn on frozen data is not cosmetic** — it makes "the snapshot
is untouched" unassertable. `.gitattributes` prevents it; the git `pre-commit`
hook in `.githooks/` catches what gets through and refuses the commit, and it
fails closed. **It is inert until `git config core.hooksPath .githooks` has
been run in this clone.** Run `python .claude/hooks/hook_test_matrix.py` to
confirm both guards are behaving.

## Publishing

**Nothing here publishes yet, and there is no remote.** The frontend is a later
session. `governance/chart-review.md` exists and is empty, ready for it; the
binding standard is `CHART-REVIEW.md` and `VIZ-PRINCIPLES.md` in
`cascadia-standards/design-system/`, not the copies in the Job Search project.

**Nothing is published unless `src/validate_measures.py` exits zero.** It
re-derives every published cell from the frozen file down a separately written
path. A measure that only agrees with itself has not been validated.

## Generated, not authored

`data/reference/dim_*.csv`, `dimension_reconciliation.md`,
`data/conformed/m0*.csv` and `governance/last_run.json` are all build outputs.
Regenerate them with the scripts in `src/`; hand-editing any of them is a
recurring failure mode and the reconciliation report says so at the top.
