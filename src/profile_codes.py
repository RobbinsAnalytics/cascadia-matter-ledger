"""Profile every coded field in the frozen IDB civil snapshot, by statistical year.

This produces the EVIDENCE for the effective-dated dimensions in Stage 2. It
does not decide anything. Its output is a per-code, per-year presence table
from which a code's effective window is derived and, where that window is
bounded, an effective-dated dimension row is written.

Reads the freeze. Writes only to data/reference/. Never modifies data/raw/.
"""
import zipfile, io, json, collections, pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
SNAPSHOT = REPO / "data" / "raw" / "cv88on.zip"
OUT = REPO / "data" / "reference" / "code_presence_by_year.json"

# Coded fields whose values are enumerated in the codebook.
CODED = ["NOS", "DISP", "PROCPROG", "JURIS", "ORIGIN", "STATUSCD", "JURY",
         "CLASSACT", "TRCLACT", "ARBIT", "NOJ", "JUDGMENT", "PROSE", "IFP",
         "TRMARB", "RESIDENC"]
# Fields the codebook says are "no longer being used" but does not date.
RETIRED = ["DJOINED", "PRETRIAL", "TRIBEGAN", "TRIALEND"]
# Fields that evidence a matter spanning more than one docket.
MULTIDOCKET = ["MDLDOCK", "TRANSDOC", "TRANSORG"]

CONTRACT_NOS = {"110", "120", "130", "140", "150", "151", "152", "153",
                "160", "190", "195", "196"}


def main():
    zf = zipfile.ZipFile(SNAPSHOT)
    fh = zf.open("cv88on.txt")
    hdr = fh.readline().decode("latin-1").rstrip("\r\n").split("\t")
    ix = {c: i for i, c in enumerate(hdr)}

    presence = {f: collections.defaultdict(collections.Counter) for f in CODED}
    populated = {f: collections.Counter() for f in RETIRED + MULTIDOCKET}
    rows_by_year = collections.Counter()
    contract_rows = 0
    contract_by_year = collections.Counter()

    for line in io.TextIOWrapper(fh, encoding="latin-1", newline=""):
        p = line.rstrip("\r\n").split("\t")
        if len(p) < len(hdr):
            continue
        year = p[ix["TAPEYEAR"]].strip()
        rows_by_year[year] += 1
        for f in CODED:
            presence[f][p[ix[f]].strip()][year] += 1
        for f in RETIRED + MULTIDOCKET:
            v = p[ix[f]].strip()
            if v and v != "-8":
                populated[f][year] += 1
        if p[ix["NOS"]].strip() in CONTRACT_NOS:
            contract_rows += 1
            contract_by_year[year] += 1

    out = {
        "snapshot_sha256_prefix": "74405231",
        "rows_by_year": dict(sorted(rows_by_year.items())),
        "contract_rows": contract_rows,
        "contract_by_year": dict(sorted(contract_by_year.items())),
        "coded_fields": {
            f: {code: dict(sorted(yrs.items())) for code, yrs in presence[f].items()}
            for f in CODED
        },
        "populated_by_year": {f: dict(sorted(populated[f].items()))
                              for f in RETIRED + MULTIDOCKET},
    }
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("rows:", f"{sum(rows_by_year.values()):,}")
    print("contract-slice rows:", f"{contract_rows:,}")
    for f in RETIRED + MULTIDOCKET:
        yrs = sorted(y for y in populated[f] if populated[f][y] > 0)
        print(f"{f:>9}: populated {sum(populated[f].values()):>10,} rows, "
              f"years {yrs[0] if yrs else '-'}..{yrs[-1] if yrs else '-'}")


if __name__ == "__main__":
    main()
