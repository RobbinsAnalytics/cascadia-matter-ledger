"""Render the page and every chart to PNG, at the design width AND at 320 px.

CHART-REVIEW v2.5 added a FAIL condition to check 7.4: renders supplied at the
design width only, with no render at the narrowest supported width. The panel
also records which widths its seats were given. So this script produces both,
every time, and names the width in every filename.

320 px is Rule 5.3 / WCAG 1.4.10 reflow, and is what CASCADIA.minCanvasPx
hard-codes. It is not a phone approximation; it is the floor the system claims
to support.

Output: docs/renders/<chart>-<width>.png plus page-<width>.png
"""
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
OUT = REPO / "docs" / "renders"
URL = "http://localhost:8731/"
DESIGN_WIDTH = 1040
NARROW_WIDTH = 320
CHARTS = ["c1", "c2", "c3", "c4", "c5"]


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("playwright is required: pip install playwright && playwright install chromium")
    OUT.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for width in (DESIGN_WIDTH, NARROW_WIDTH):
            page = browser.new_page(viewport={"width": width, "height": 1400},
                                    device_scale_factor=2)
            errors = []
            page.on("console", lambda m: errors.append(m.text)
                    if m.type == "error" else None)
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(URL, wait_until="networkidle")
            page.wait_for_timeout(1200)

            if errors:
                print("  CONSOLE ERRORS at %dpx:" % width)
                for e in errors[:8]:
                    print("    " + e)

            page.screenshot(path=str(OUT / ("page-%d.png" % width)),
                            full_page=True)
            for cid in CHARTS:
                card = page.locator("#%s" % cid).locator(
                    "xpath=ancestor::div[contains(@class,'chart-card')]")
                target = card if card.count() else page.locator("#%s" % cid)
                target.screenshot(path=str(OUT / ("%s-%d.png" % (cid, width))))
                print("  %s-%d.png" % (cid, width))

            # Report the rendered provenance segment count -- CHART-REVIEW K5
            # fails a chart whose RENDERED strip does not carry the declared
            # number of segments, and only a render can tell you that.
            seg = page.evaluate(
                """() => Array.from(document.querySelectorAll('.cascadia-provenance'))
                        .map(n => n.textContent.split(' \\u00b7 ').length)""")
            dims = page.evaluate(
                """() => Object.fromEntries(['c1','c2','c3','c4','c5'].map(id => {
                     const cv = document.getElementById(id).querySelector('canvas');
                     return [id, cv ? cv.width + 'x' + cv.height : 'none'];
                   }))""")
            print("  width %d: strip segments %s" % (width, seg))
            print("  width %d: canvas %s" % (width, dims))
            page.close()
        browser.close()
    print("\nrenders in docs/renders/")


if __name__ == "__main__":
    main()
