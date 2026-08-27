# The docket-event derivation rule

*Stage 5 artifact. **Written before the code that implements it**, and before
any derived output was produced. Owner: Aaron Robbins. Established 2026-08-26.*

---

## What this rule is for

The frozen IDB tells you how a matter *ended*: `PROCPROG` records the point the
case had reached when it was disposed of, and `DISP` records how. It cannot tell
you what happened *along the way*. That is not a gap in the extract; it is a
property of the source, recorded as `docket-to-matter.md` L-06 — the publisher
replaces a case's record on each refresh rather than appending to it.

**Motion practice is the clearest example of what is therefore invisible.** How
many motions a matter attracts is a first-order driver of outside-counsel spend,
and it is exactly the kind of question a legal-operations team is asked. The
frozen model cannot answer it at any grain.

The live edge can, because a docket entry is a document with text in it. This
rule is how that text becomes a row.

> **The point is not text processing. The point is that a document became a
> governed row by a written rule, with a named owner, and the rule states what
> it gets wrong.**

## R-05 · The rule

> **A docket entry is classified as exactly one `docket_event_type`, determined
> solely by the first recognised event keyword at the START of its
> `description` field, after stripping leading punctuation and whitespace.**
>
> **If no keyword matches at the start, the event type is `UNCLASSIFIED`. It is
> never guessed from elsewhere in the text.**

The controlled vocabulary is small and closed:

| `docket_event_type` | Leading keyword |
|---|---|
| `COMPLAINT` | COMPLAINT |
| `MOTION` | MOTION |
| `ORDER` | ORDER |
| `ANSWER` | ANSWER |
| `NOTICE` | NOTICE |
| `STIPULATION` | STIPULATION |
| `JUDGMENT` | JUDGMENT, CLERK'S JUDGMENT |
| `DECLARATION` | DECLARATION |
| `RESPONSE` | RESPONSE, REPLY, OPPOSITION |
| `TRANSCRIPT` | TRANSCRIPT |
| `SUMMONS` | SUMMONS |
| `UNCLASSIFIED` | *no leading keyword matched* |

## R-05.a · Position is the whole rule, and it is not a technicality

**A naive implementation would search the description for the word "MOTION"
anywhere.** That is wrong, and it is wrong in a specific, one-directional way
that inflates the answer:

> `ORDER granting MOTION for Summary Judgment`

This is an **order**. The court ruled. Counting it as a motion filing counts the
same motion twice — once when filed, once when decided — and every contested
motion generates at least one such order, often several. A substring match does
not produce a slightly high motion count; it roughly doubles it, and it does so
more for hard-fought matters than for easy ones, which is precisely the
comparison anyone would want to make.

**The keyword must appear at position zero.** That single constraint is the
difference between a number and a wrong number, and it is why this rule exists
as a document rather than as a `LIKE '%MOTION%'` inside a query.

## R-05.b · One entry, one event

An entry is classified once. Entries frequently reference several document
types (`MOTION for Leave to Proceed in forma pauperis filed by ... (Filed on
8/18/2026)`), and only the leading one is the act the entry records.

## R-05.c · Empty descriptions are `UNCLASSIFIED`, and are counted

Some entries carry no description at all — the record exists because a document
was filed under seal, or because RECAP holds the docket line without its text.
These are **not dropped**. They are classified `UNCLASSIFIED` and counted, and
the count is published on every run. An entry with no text is evidence that
something happened; discarding it would silently shrink every denominator.

---

## What this rule loses

**D-01 · It classifies the entry, not the document.** One docket entry may
attach several documents. The event is the docket act, not each attachment.

**D-02 · `MOTION` counts motions *filed*, not motions *granted*.** Outcome is
not derivable from a leading keyword and this rule does not attempt it. Any
question about success rates is out of scope and must not be answered from this
field.

**D-03 · Court clerks are not consistent.** The description is free text typed
by court staff. Local conventions differ between districts and drift over time.
A vocabulary calibrated on one court is not automatically valid in another, and
this module's slice is deliberately a single court for that reason.

**D-04 · `UNCLASSIFIED` is a real category, not a failure bucket.** Its rate is
a health metric. A sudden rise means the court changed its conventions or the
vocabulary has decayed, and that is a signal the pipeline is designed to
surface rather than absorb.

**D-05 · Coverage is not completeness.** RECAP holds what someone has purchased
or contributed from PACER. A docket with few entries here may be a quiet docket
or a poorly covered one, and **this rule cannot distinguish the two.** Motion
counts are therefore reported as *observed* motions, never as *the* number of
motions, and no measure derived from them is certified under
`metric_register.md` until coverage itself is modelled.

---

## How this rule is enforced

| # | Assertion | On failure |
|---|---|---|
| EV-1 | Every ingested entry has exactly one `docket_event_type` | Run fails |
| EV-2 | No entry is classified by a keyword found after position zero | Run fails |
| EV-3 | The `UNCLASSIFIED` rate is recorded every run | Run marked incomplete |
| EV-4 | Entries with empty descriptions are retained, not dropped | Run fails |

Re-asserted on **every** run, not once at build time.

## Changing this rule

The vocabulary is versioned with this document. Adding a keyword changes every
historical count derived under it, so a change is a dated amendment with a
restatement of what moved — never a silent edit to a list.
