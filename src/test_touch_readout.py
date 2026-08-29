"""The tap readout must land in the VIEWPORT, with the chart top above the fold.

WHY THIS TEST EXISTS, AND WHY IT IS SHAPED LIKE THIS.

The touch readout was reported broken on a real phone three times, and three
rounds of harness said it worked. It did work -- in the harness. Every one of
those tests called `scrollIntoView({block:'center'})` before tapping, which put
the chart container's top back on screen. The readout was being drawn at the
container's top-left, so scrolling the container into view was precisely the
condition under which the bug could not appear. The harness established that
condition, then reported success, three times running.

On a phone you scroll until the PLOT fills the screen, which puts the title and
subtitle above the fold. The box drew up there, off screen, while the axis
pointer stayed visible in the plot. "Vertical line, no textbox" was an exact
description of what was happening.

SO THIS TEST MUST NEVER CALL scrollIntoView. It deliberately scrolls each
chart's container top ABOVE the viewport, at two depths, and asserts the readout
is inside the VIEWPORT rather than inside the container. Those two are not the
same box, and the difference is the whole defect.

Two further traps, both of which produced a false "no readout" while the page
was fine:

  * Tapping a fixed fraction of the plot sends the point off screen once the
    chart is scrolled far enough. A tap that lands nowhere is indistinguishable
    from a readout that never appears. This taps the centre of the plot's
    VISIBLE portion and skips a chart whose plot is not on screen at all.
  * On a sorted bar chart with a long tail, most bars do not reach the middle of
    the plot. A tap at 45% of the width hits empty canvas on `c5`. Bar charts
    are tapped near the left edge, where every bar has ink.

Run:  python src/test_touch_readout.py
Exit: 0 if every chart passes at every depth, 1 otherwise.
"""
import functools
import http.server
import io
import pathlib
import socketserver
import sys
import threading

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO = pathlib.Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"
PORT = 8773
VIEWPORT = {"width": 390, "height": 844}

# How far above the fold to push the container's top, in px.
DEPTHS = (140, 420)

# Where to tap, as a fraction of the plot rect. Bar charts get a tap near the
# left edge because their long tail has no ink at mid-plot.
TAPS = {"c1": (0.45, 0.06), "c2": (0.45, 0.50), "c3": (0.05, 0.35),
        "c4": (0.04, 0.06), "c5": (0.04, 0.06)}

SCROLL = """([id, above, fx, fy]) => {
  const h = document.getElementById(id);
  scrollBy(0, h.getBoundingClientRect().top + above);
  const r = h.getBoundingClientRect();
  const g = echarts.getInstanceByDom(h).getModel()
              .getComponent('grid').coordinateSystem.getRect();
  const plotTop = r.y + g.y, plotBot = r.y + g.y + g.height;
  const visTop = Math.max(plotTop, 8), visBot = Math.min(plotBot, innerHeight - 8);
  if (visBot - visTop < 24) return {skip: true};
  const wantY = r.y + g.y + g.height * fy;
  return {containerTop: Math.round(r.top),
          tapX: r.x + g.x + g.width * fx,
          tapY: Math.min(Math.max(wantY, visTop + 12), visBot - 12)};
}"""

CHECK = """(id) => {
  const h = document.getElementById(id);
  const els = [...h.querySelectorAll('div')].filter(d =>
    /position:\\s*absolute/.test(d.getAttribute('style') || '') &&
    (d.textContent || '').trim().length > 3);
  if (!els.length) return {found: false};
  const d = els[els.length - 1], r = d.getBoundingClientRect(),
        cs = getComputedStyle(d);
  return {found: true, vis: cs.visibility,
          top: Math.round(r.top), bottom: Math.round(r.bottom),
          inViewport: r.top >= 0 && r.bottom <= innerHeight &&
                      r.left >= 0 && r.right <= innerWidth,
          text: d.textContent.trim().slice(0, 40)};
}"""


def main():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=str(DOCS))
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.TCPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("playwright is required: pip install playwright && "
                 "playwright install chromium")

    failures = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for above in DEPTHS:
            print("--- container top %d px above the fold ---" % above)
            for cid, (fx, fy) in TAPS.items():
                ctx = browser.new_context(viewport=VIEWPORT, has_touch=True,
                                          is_mobile=True)
                page = ctx.new_page()
                page.goto("http://127.0.0.1:%d/" % PORT, wait_until="networkidle")
                page.wait_for_timeout(750)
                pos = page.evaluate(SCROLL, [cid, above, fx, fy])
                if pos.get("skip"):
                    print("  %s  SKIP  plot not on screen at this depth" % cid)
                    ctx.close()
                    continue
                page.wait_for_timeout(200)
                page.touchscreen.tap(pos["tapX"], pos["tapY"])
                page.wait_for_timeout(450)
                r = page.evaluate(CHECK, cid)
                ok = (r.get("found") and r.get("inViewport")
                      and r.get("vis") == "visible")
                if not ok:
                    failures.append((above, cid, r))
                print("  %s  %-4s  top=%s bottom=%s  %r"
                      % (cid, "PASS" if ok else "FAIL", r.get("top"),
                         r.get("bottom"), r.get("text", "")))
                ctx.close()
        browser.close()
    srv.shutdown()

    print()
    if failures:
        print("FAILED -- the readout was not inside the viewport:")
        for above, cid, r in failures:
            print("  %s at depth %d: %s" % (cid, above, r))
        sys.exit(1)
    print("PASS -- readout inside the viewport at every chart and depth")


if __name__ == "__main__":
    main()
