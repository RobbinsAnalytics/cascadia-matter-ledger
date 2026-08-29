"""Render the page and every chart across the K6 width ladder.

CHART-REVIEW K6 is an INVARIANT: the review is run "at the narrowest width, the
design width, and +/-1 px either side of every declared breakpoint." This script
used to render 1040 and 320 and nothing else, which is not K6 -- and the module
passed a reading panel anyway.

WHAT THAT COST. Chart 1 drew its value labels inside their own bars, because a
narrow-only branch anchored the label to the row centre instead of the bar. The
branch exists below 560. Rendering 559 beside 561 puts that flip under direct
comparison, and K6 requires exactly those two renders. The check that would have
caught the build's most expensive defect already existed and was simply not run.

So the ladder is no longer typed here. It is DERIVED from
`window.CASCADIA_BREAKPOINTS`, declared once in docs/assets/page.js: a breakpoint
that is used must be declared, and a declared breakpoint is rendered whether
anyone remembers it or not.

320 px is Rule 5.3 / WCAG 1.4.10 reflow and what CASCADIA.minCanvasPx hard-codes.
It is not a phone approximation; it is the floor the system claims to support.

Also checked at every width, because both were found the hard way:
  * horizontal overflow -- Rule 5.3's 1.4.10 clause, asserted rather than assumed
  * the real ECharts grid rect -- page.js estimated it 42% high at 320 px, and
    since axis padding is proportional to 1/plotPx an over-estimate UNDER-reserves
    label room. An estimate that is never compared to the truth stays wrong.

Output: docs/renders/<chart>-<width>.png plus page-<width>.png
Exit non-zero if any width overflows horizontally.
"""
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
OUT = REPO / "docs" / "renders"
URL = "http://localhost:8731/"
DESIGN_WIDTH = 1040
NARROW_WIDTH = 320
# Upper bound for the breakpoint search. Above the design width the page
# stops changing shape, so a crossing beyond this is not one a reader meets.
SEARCH_MAX = 1600
CHARTS = ["c1", "c2", "c3", "c4", "c5"]


def k6_ladder(browser):
    """The K6 ladder, derived from what the page declares -- and translated.

    K6 asks for "+/-1 px either side of every declared breakpoint". The subtle
    part, which cost a round here: `layout()` branches on the CHART HOST width,
    not the viewport, and the host is ~66 px narrower than the viewport for a
    full-width chart and roughly half of it for one in the two-column grid.
    Rendering viewport 559 and 561 against a host breakpoint of 560 leaves
    `narrow` TRUE on both sides -- two renders that straddle nothing and a
    ladder that looks right while testing the same branch twice.

    So for every (chart, breakpoint) pair this binary-searches the viewport
    width at which that chart's host actually crosses the breakpoint, and asks
    for the two viewports either side of the crossing. That is the render pair
    K6 is describing.

    Returns (widths, breakpoints, crossings) where crossings is a list of
    (chart, breakpoint, viewport) so the log can show its work.
    """
    page = browser.new_page(viewport={"width": DESIGN_WIDTH, "height": 900})
    page.goto(URL, wait_until="networkidle")
    page.wait_for_timeout(500)
    bps = page.evaluate("() => window.CASCADIA_BREAKPOINTS || null")
    if not bps:
        page.close()
        sys.exit("page.js declares no window.CASCADIA_BREAKPOINTS, so the K6 "
                 "ladder cannot be derived. Fail closed rather than fall back "
                 "to a typed pair -- a typed pair is what let K6 go unrun.")

    def host_width(viewport, cid):
        page.set_viewport_size({"width": viewport, "height": 900})
        page.wait_for_timeout(60)
        return page.evaluate("(id) => document.getElementById(id).clientWidth",
                             cid)

    widths = {NARROW_WIDTH, DESIGN_WIDTH}
    crossings = []
    for cid in CHARTS:
        for b in bps:
            lo, hi = NARROW_WIDTH, SEARCH_MAX
            if host_width(hi, cid) < b:
                continue          # this chart never reaches that breakpoint
            if host_width(lo, cid) >= b:
                continue          # it is past it even at the floor
            while hi - lo > 1:    # smallest viewport whose host >= b
                mid = (lo + hi) // 2
                if host_width(mid, cid) >= b:
                    hi = mid
                else:
                    lo = mid
            crossings.append((cid, b, hi))
            widths.add(lo)
            widths.add(hi)
    page.close()
    return sorted(widths), list(bps), crossings


def main():
    # `render_charts.py 630 768 --out <dir>` still renders explicit widths
    # somewhere else. With no widths given you get the K6 ladder, derived.
    argv = sys.argv[1:]
    out_dir = OUT
    if "--out" in argv:
        i = argv.index("--out")
        out_dir = pathlib.Path(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    widths = [int(a) for a in argv if a.isdigit()]
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("playwright is required: pip install playwright && playwright install chromium")
    out_dir.mkdir(parents=True, exist_ok=True)

    overflow_failures = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        if widths:
            print("explicit widths: %s" % ", ".join(str(w) for w in widths))
        else:
            widths, bps, crossings = k6_ladder(browser)
            print("K6 ladder derived from declared breakpoints %s"
                  % ", ".join(str(b) for b in bps))
            for cid, b, v in crossings:
                print("  %s crosses host %d px between viewport %d and %d"
                      % (cid, b, v - 1, v))
            print("  widths: %s" % ", ".join(str(w) for w in widths))
        for width in widths:
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

            page.screenshot(path=str(out_dir / ("page-%d.png" % width)),
                            full_page=True)
            for cid in CHARTS:
                card = page.locator("#%s" % cid).locator(
                    "xpath=ancestor::div[contains(@class,'chart-card')]")
                target = card if card.count() else page.locator("#%s" % cid)
                target.screenshot(path=str(out_dir / ("%s-%d.png" % (cid, width))))
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
            # A3 -- the REAL grid rect, not the estimate in page.js. That
            # estimate read 146 px where the truth was 103, and because axis
            # padding goes as 1/plotPx an over-estimated plot UNDER-reserves
            # label room. Printing both turns a silent 42% error into a line
            # in a log that someone can notice.
            grid = page.evaluate(
                """() => Object.fromEntries(['c1','c2','c3','c4','c5'].map(id => {
                     try {
                       const ch = echarts.getInstanceByDom(
                         document.getElementById(id));
                       const g = ch.getModel().getComponent('grid')
                                  .coordinateSystem.getRect();
                       return [id, Math.round(g.width)];
                     } catch (e) { return [id, 'n/a']; }
                   }))""")
            # A4 -- Rule 5.3 adopts WCAG 1.4.10 reflow. It was adopted and
            # never tested: a sibling page shipped 542 px wide at a 390 px
            # viewport underneath a green accessibility check.
            over = page.evaluate(
                """() => ({scroll: document.documentElement.scrollWidth,
                          client: document.documentElement.clientWidth})""")
            print("  width %d: strip segments %s" % (width, seg))
            print("  width %d: canvas %s" % (width, dims))
            print("  width %d: grid px %s" % (width, grid))
            if over["scroll"] > over["client"] + 1:
                overflow_failures.append((width, over["scroll"], over["client"]))
                print("  width %d: HORIZONTAL OVERFLOW  scrollWidth %d > "
                      "clientWidth %d"
                      % (width, over["scroll"], over["client"]))
            page.close()
        browser.close()

    print("\nrenders in %s" % out_dir)
    if overflow_failures:
        print("\nRULE 5.3 / WCAG 1.4.10 FAILED -- the page scrolls sideways:")
        for w, sw, cw in overflow_failures:
            print("  at %d px the document is %d px wide (over by %d)"
                  % (w, sw, sw - cw))
        sys.exit(1)


if __name__ == "__main__":
    main()
