"""Build the conformed dimensions FROM THE PUBLISHED CODEBOOK.

The governance centrepiece of this module. Code meanings are parsed out of the
FJC's own codebook PDF and joined to the observed year-by-year presence of each
code in the frozen snapshot. Nothing here hardcodes a code meaning, and no
query downstream contains a CASE WHEN over a code value.

Two outputs:

  data/reference/dim_<field>.csv               one row per code, with its window
  data/reference/dimension_reconciliation.md   what the codebook and the data
                                               disagree about

The reconciliation is not a by-product. A dimension built from a document is
only trustworthy if something checks the document against the data, and that
check is why this parser is allowed to be imperfect: a code the parser misses
shows up as "observed but undocumented" and is impossible to overlook.

Inputs are the committed codebook PDF and code_presence_by_year.json. This
script does not open data/raw/cv88on.zip -- run src/profile_codes.py first.
"""
import csv
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
CODEBOOK = REPO / "data" / "raw" / "civil_codebook_1988_forward_20231025.pdf"
PRESENCE = REPO / "data" / "reference" / "code_presence_by_year.json"
REFDIR = REPO / "data" / "reference"

SY_MIN, SY_MAX = 1988, 2026

# A code's window is treated as bounded only if it is BOTH absent at a boundary
# and material. Five rows in one year is a keying error, not a code change.
# The threshold is a governance decision and it is stated in the report.
MATERIAL_ROWS = 100

# Values that are not codes and must never be counted as undocumented ones.
# "-8" is the codebook's own missing marker, stated once in the front matter
# rather than repeated in every field's list; the empty string is the absence
# of a value. Both are real and both are reported, separately, because rolling
# them into the undocumented-code count would inflate it by three million rows
# and make the headline figure indefensible.
SENTINELS = {"-8", ""}

# The codebook PDF renders its separator inconsistently -- hyphen-minus in some
# field definitions, an en dash in others, and a replacement character wherever
# the extractor could not resolve the glyph. Match any of them.
DASH = "[" + "".join([
    "-",  # hyphen-minus
    "‐", "‑", "‒", "–", "—", "―",  # dashes
    "−",  # minus sign
    "�",  # replacement char, from unresolved glyphs
]) + "]"

# field -> (segment start marker, segment end marker, code pattern)
SPECS = {
    "NOS": ("(NOS)", "Must have appropriate jurisdiction",
            r"^\s*(\d{3})\s+(\S.*)$"),
    "DISP": ("DISPOSITION \n(DISP)", "NATURE OF JUDGMENT",
             r"^\s*(\d{1,2})\s*" + DASH + r"+\s*(\S.*)$"),
    "PROCPROG": ("PROCEDURAL PROGRESS \n(PROCPROG)", "See Appendix A",
                 r"^\s*(\d{1,2})\s*" + DASH + r"+\s*(\S.*)$"),
    "ORIGIN": ("(ORIGIN)", "JURISDICTION",
               r"^\s*(\d{1,2})\s*" + DASH + r"+\s*(\S.*)$"),
    "JURIS": ("(JURIS)", "NATURE OF SUIT",
              r"^\s*(\d)\s*" + DASH + r"+\s*(\S.*)$"),
    "STATUSCD": ("STATUS CODE \n(STATUSCD)", "YEAR OF TAPE",
                 r"^\s*([SL])\s*" + DASH + r"+\s*(\S.*)$"),
}

# Effective dates the codebook states in prose rather than in a code list.
# Recorded so the derived window can be checked against the publisher's own
# claim. Where the two agree, the derivation method is validated on a case
# where the answer is independently known.
PUBLISHED_START = {
    "STATUSCD": (2001, 'codebook: "This field captured since October 2000"'),
    "IFP": (2001, 'codebook: "This field captured since October 2000"'),
    "PROSE": (1996, 'codebook: "Pro Se field is blank in records posted '
                    'before October 1995"'),
}


def codebook_text():
    try:
        import pypdf
    except ImportError:
        sys.exit("pypdf is required: pip install pypdf")
    reader = pypdf.PdfReader(str(CODEBOOK))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def parse_procprog_groups(text):
    """PROCPROG codes are only meaningful inside their group.

    Codes 1 and 3 both read "no court action" and they are not the same state:
    one is before issue was joined, the other after. The codebook carries the
    distinction as "a) before issue joined" / "b) after issued joined" headers
    above the code lists, and a dimension that keeps only code and description
    silently merges 379,357 matters in this slice into one ambiguous label.
    """
    i = text.find("PROCEDURAL PROGRESS \n(PROCPROG)")
    segment = text[i:text.find("See Appendix A", i)]
    groups, current = {}, ""
    for line in segment.splitlines():
        header = re.match(r"\s*[ab]\)\s*(.+?)\s*$", line)
        if header:
            current = header.group(1).strip()
            continue
        m = re.match(r"^\s*(\d{1,2})\s*" + DASH + r"+\s*\S", line)
        if m and current:
            groups.setdefault(m.group(1), current)
    return groups


def parse_field(text, start, end, pattern):
    i = text.find(start)
    if i < 0:
        raise SystemExit("codebook segment not found: %r" % start)
    j = text.find(end, i + len(start))
    segment = text[i:j if j > 0 else len(text)]
    out = {}
    for line in segment.splitlines():
        m = re.match(pattern, line)
        if m:
            out.setdefault(m.group(1), re.sub(r"\s+", " ", m.group(2).strip()))
    return out


def window(year_counts):
    """First and last statistical year a code appears, and its total rows."""
    years = sorted(int(y) for y, n in year_counts.items()
                   if y.isdigit() and SY_MIN <= int(y) <= SY_MAX and n > 0)
    total = sum(n for y, n in year_counts.items()
                if y.isdigit() and SY_MIN <= int(y) <= SY_MAX)
    return (years[0], years[-1], total) if years else (None, None, total)


def main():
    text = codebook_text()
    presence = json.loads(PRESENCE.read_text(encoding="utf-8"))

    report = [
        "# Dimension reconciliation",
        "",
        "*Generated by `src/build_dimensions.py` from the committed codebook PDF",
        "and the frozen snapshot. Regenerate it; never hand-edit it.*",
        "",
        "A code's effective window is called **bounded** when the code is absent",
        "at a boundary of the %d-%d range **and** appears on more than %d rows."
        % (SY_MIN, SY_MAX, MATERIAL_ROWS),
        "The threshold exists so that a handful of keying errors in a single year",
        "is not reported as a code change. It is a judgment, it is stated here,",
        "and it is the only one in this file.",
        "",
    ]
    totals = {"bounded": 0, "undocumented": 0, "undocumented_rows": 0,
              "sentinel_rows": 0, "undocumented_states": 0,
              "undocumented_state_rows": 0}

    procprog_groups = parse_procprog_groups(text)

    for field, (start, end, pattern) in SPECS.items():
        documented = parse_field(text, start, end, pattern)
        observed = presence["coded_fields"][field]
        rows, bounded, undocumented, sentinels = [], [], [], []

        for code in sorted(set(documented) | set(observed),
                           key=lambda c: (len(c), c)):
            first, last, n = window(observed.get(code, {}))
            if n == 0 and code not in documented:
                continue
            is_bounded = (first is not None
                          and (first > SY_MIN or last < SY_MAX)
                          and n > MATERIAL_ROWS)
            if code in SENTINELS:
                status = ("missing marker" if code == "-8"
                          else "absent, undocumented state")
            elif n == 0:
                status = "documented, never observed"
            elif code in documented:
                status = "documented"
            else:
                status = "undocumented"
            row = {
                "code": code,
                "description": documented.get(
                    code, "(not in this codebook revision)"),
                "effective_from_sy": first if first else "",
                "effective_to_sy": last if last else "",
                "observed_rows": n,
                "window": ("bounded" if is_bounded
                           else ("full" if first else "none")),
                "codebook_status": status,
            }
            if field == "PROCPROG":
                row["group"] = procprog_groups.get(code, "")
                row["qualified_description"] = (
                    "%s, %s" % (row["description"], row["group"])
                    if row["group"] else row["description"])
            rows.append(row)
            if is_bounded and code not in SENTINELS:
                bounded.append((code, first, last, n))
            if status == "undocumented":
                undocumented.append((code, first, last, n))
            if code in SENTINELS and n:
                sentinels.append((code, first, last, n, status))

        with (REFDIR / ("dim_%s.csv" % field.lower())).open(
                "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

        undoc_rows = sum(r[3] for r in undocumented)
        totals["bounded"] += len(bounded)
        totals["undocumented"] += len(undocumented)
        totals["undocumented_rows"] += undoc_rows
        totals["sentinel_rows"] += sum(r[3] for r in sentinels if r[0] == "-8")
        for s in sentinels:
            if s[0] == "":
                totals["undocumented_states"] += 1
                totals["undocumented_state_rows"] += s[3]

        observed_distinct = len([c for c in observed
                                 if c not in SENTINELS and window(observed[c])[2]])
        report += [
            "## %s -- `dim_%s.csv`" % (field, field.lower()),
            "",
            "- codes in the codebook: **%d**" % len(documented),
            "- distinct codes in the data, sentinels excluded: **%d**"
            % observed_distinct,
            "- codes with a bounded effective window: **%d**" % len(bounded),
            "- codes in the data this codebook revision does not document: "
            "**%d**, covering **%s** rows" % (len(undocumented),
                                              format(undoc_rows, ",")),
            "",
        ]
        if undocumented:
            report += ["| code | first SY | last SY | rows |", "|---|---|---|---|"]
            report += ["| `%s` | %s | %s | %s |" % (c, f, l, format(n, ","))
                       for c, f, l, n in sorted(undocumented,
                                                key=lambda r: -r[3])]
            report += [""]
        if sentinels:
            report += ["Sentinels, reported separately because they are not codes:",
                       "", "| value | first SY | last SY | rows | reading |",
                       "|---|---|---|---|---|"]
            report += ["| %s | %s | %s | %s | %s |"
                       % ("`-8`" if c == "-8" else "*(empty)*", f, l,
                          format(n, ","), st)
                       for c, f, l, n, st in sorted(sentinels, key=lambda r: -r[3])]
            report += [""]
        if field in PUBLISHED_START and bounded:
            # Compare against the DOCUMENTED codes only. A sentinel's window
            # says when the field was blank, not when the field began.
            derived = min(b[1] for b in bounded)
            claimed, cite = PUBLISHED_START[field]
            verdict = "MATCHES" if derived == claimed else "DIFFERS FROM"
            report += [
                "**Derived start %d %s the published start %d** -- %s."
                % (derived, verdict, claimed, cite),
                "",
            ]

    report += [
        "## Totals",
        "",
        "- codes with a bounded effective window: **%d**" % totals["bounded"],
        "- codes present in the data that this codebook revision does not "
        "document: **%d**, covering **%s** rows"
        % (totals["undocumented"], format(totals["undocumented_rows"], ",")),
        "- undocumented *states* -- a field empty across a bounded run of years: "
        "**%d**, covering **%s** rows"
        % (totals["undocumented_states"],
           format(totals["undocumented_state_rows"], ",")),
        "- rows carrying the codebook's documented `-8` missing marker on one of "
        "these fields: **%s**" % format(totals["sentinel_rows"], ","),
        "",
        "The second and third numbers are the argument for effective-dated",
        "dimensions, and they fail differently. An undocumented **code** cannot be",
        "decoded by a `CASE WHEN` written from the current codebook: it falls",
        'through to null or to "other", silently, and raises no error. An',
        "undocumented **state** is worse, because a field that is simply empty for",
        "thirteen years reads as a data-quality problem rather than as a field",
        "that did not exist yet, and the usual reflex is to filter those rows out.",
        "",
    ]
    (REFDIR / "dimension_reconciliation.md").write_text(
        "\n".join(report), encoding="utf-8")
    print("\n".join(report[-9:]))


if __name__ == "__main__":
    main()
