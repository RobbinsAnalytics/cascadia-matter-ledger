# Cascadia Matter Ledger

A governed dimensional model built from the **public federal civil docket**,
with legal-operations certified measures on top, and a scheduled incremental
pipeline that re-asserts its own invariants on every run and publishes what it
found — including when a check fails.

**Source:** the Federal Judicial Center's Integrated Database, civil cases
filed, terminated and pending, statistical year 1988 forward. 10,960,173 case
records. Frozen 2026-08-26; see `governance/source-register.md` for the hash
and the retrieval receipts.

**Status:** data layer under construction. No published figures yet.

## Why "Ledger"

A ledger is a record that balances, and the balancing is the point. The live
increment reconciles against the frozen baseline on every run, and the
reconciliation is published whether it passes or fails.

## Why "Matter"

A docket is not a matter. A docket is the court's record of a case; a matter is
a legal department's internal unit of work. The mapping between them is a
written, owned rule that states what it loses — see
`governance/docket-to-matter.md` — not an assumption buried in a join.

## Repository and folder names differ on purpose

The local working folder is `cascadia-matter-ledger-analytics`; the GitHub
remote is `cascadia-matter-ledger`. The `-analytics` suffix is the local
estate's convention for a module build. **Neither is a typo. Do not rename
either to match the other.**
