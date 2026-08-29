/**
 * Cascadia Matter Ledger — chart layer.
 *
 * Reads the build-time data block written by src/build_page.py. No figure is
 * computed here that is not already in that block (Rule K2); this file decides
 * geometry, not values.
 *
 * Responsive behaviour follows Rule 5.5's drop order. What narrows: axis tick
 * density, annotation prose (moved out of the plot, marker kept), and category
 * label length via the DECLARED mapping in ABBREV below. What never drops:
 * the title, the axis units, the data table, and any direct label.
 */
(function () {
  'use strict';

  var D = JSON.parse(document.getElementById('cascadia-data').textContent);
  var C = CASCADIA.colors, INK = CASCADIA.textInk;
  var SANS = '"Segoe UI",-apple-system,"Helvetica Neue",Arial,sans-serif';
  var SOURCE = 'FJC Integrated Database, federal civil dockets';
  var ASOF = 'frozen ' + D.asOf;

  function el(id) { return document.getElementById(id); }
  function nf(n) { return Number(n).toLocaleString('en-US'); }

  /**
   * Rule 5.5 — a direct label may be abbreviated by a DECLARED mapping and
   * never deleted. This is that mapping. It applies only below 560 px.
   */
  var ABBREV = {
    'Recovery of Overpayments of Vet Benefits': 'Vet benefit overpayments',
    'Recovery of Defaulted Student Loans': 'Defaulted student loans',
    'Overpayments & Enforcement of Judgments': 'Overpayment enforcement',
    'Overpayments under the Medicare Act': 'Medicare overpayments',
    'Other Contract Actions': 'Other contract',
    'Marine Contract Actions': 'Marine contract',
    'Negotiable Instruments': 'Negotiable instruments',
    'Contract Product Liability': 'Contract product liability',
    "Stockholder's Suits": "Stockholder's suits",
    'transfer to another district': 'transfer to another district',
    'multi district litigation transfer': 'MDL transfer',
    'appeal affirmed (magistrate judge)': 'appeal affirmed (mag.)',
    'appeal denied (magistrate judge)': 'appeal denied (mag.)',
    'no court action, before issue joined': 'no court action, before issue',
    'no court action, after issued joined': 'no court action, after issue',
    'judgement on motion, after issued joined': 'judgment on motion, after issue',
    'pretrial conference held, after issued joined': 'pretrial conference, after issue',
    'order entered, before issue joined': 'order entered, before issue',
    'order decided, before issue joined': 'order decided, before issue',
    'hearing held, before issue joined': 'hearing held, before issue',
    'after court trial, after issued joined': 'after court trial',
    'after jury trial, after issued joined': 'after jury trial',
    'during court trial, after issued joined': 'during court trial',
    'during jury trial, after issued joined': 'during jury trial',
    'other, after issued joined': 'other, after issue',
    'request for trial de novo after, after issued joined': 'trial de novo requested'
  };

  /**
   * How much vertical room the title block will actually take once wrapped.
   *
   * A fixed grid.top was wrong at 320 px: the title wraps to five lines there
   * and the subtitle to four, and the plot was drawn underneath both. Nothing
   * in the config reports this — only a render does. Measured with a canvas
   * text metric rather than estimated from character counts, because the
   * serif title and the sans subtitle have very different advance widths.
   */
  var _m = document.createElement('canvas').getContext('2d');
  function wrappedLines(text, px, font) {
    _m.font = font;
    var words = String(text).split(' '), lines = 1, cur = '';
    for (var i = 0; i < words.length; i++) {
      var test = cur ? cur + ' ' + words[i] : words[i];
      if (_m.measureText(test).width > px && cur) { lines++; cur = words[i]; }
      else { cur = test; }
    }
    return lines;
  }
  function titleTop(w, finding, subtitle) {
    var tl = wrappedLines(finding, w - 8,
      '600 20px "Source Serif 4", Georgia, serif');
    var sl = wrappedLines(subtitle, w - 8,
      '13px "Segoe UI", Arial, sans-serif');
    return Math.round(10 + tl * 26 + 8 + sl * 18 + 16);
  }

  /** Geometry that depends on how much room there actually is. */
  function layout(host) {
    var w = host.clientWidth || CASCADIA.minCanvasPx;
    var narrow = w < 560;
    return {
      w: w,
      narrow: narrow,
      // Proportional at every width, not only below 560. A fixed 230 px
      // label column plus a 92 px right gutter squeezed the plot at ~630 px
      // until outside-the-bar labels landed back on top of the bars. That
      // width sat between the two rendered widths and so was never checked.
      labelWidth: Math.max(96, Math.min(230, Math.round(w * 0.30))),
      gridRight: narrow ? 46 : 92,
      // What CHART-REVIEW 5.5 fails is a HOVER-FOLLOWING tooltip at <=768 px,
      // and the reason is touch: there is no hover, and a readout that chases
      // the finger covers the mark it is describing. The old gate here read
      // the WIDTH instead of the capability, which got both cases wrong -- a
      // narrow desktop window has a mouse and lost its tooltip anyway, and a
      // phone lost it for a reason that was never about size.
      //
      // So: ask the pointer what it is. A fine pointer that can hover keeps
      // the hover tooltip at every width. Everything else gets the same
      // readout on TAP, anchored above the plot rather than under the finger
      // -- which is not a hover-following tooltip and does not engage 5.5.
      // The data tables remain the guaranteed layer either way (Rule 5.1).
      tooltip: true,
      tapTip: !(window.matchMedia &&
                window.matchMedia('(hover: hover) and (pointer: fine)').matches),
      abbrev: function (s) { return narrow && ABBREV[s] ? ABBREV[s] : s; }
    };
  }

  /**
   * Tooltip config, or `{show:false}` below 769 px.
   *
   * A tooltip does NOT move this artifact to Checklist B. That list is for
   * "any artifact whose finding belongs to the reader"; every finding here is
   * fixed in a title and a tooltip moves none of them. Rule 5.5 governs
   * tooltips inside Checklist A, and Rule 4.4 names the tooltip as the home
   * for full precision. The provenance strip therefore stays at THREE
   * segments -- 4.4's fourth segment is required only where a control changes
   * what is shown, and this changes nothing.
   *
   * Styling comes from the theme's own tooltip block. Nothing is invented.
   */
  function tip(L, opts) {
    if (!L.tooltip) return { show: false };
    return {
      show: true,
      trigger: opts.trigger || 'item',
      confine: true,
      appendToBody: false,
      // On touch the readout is summoned by a tap and pinned to the top of
      // the chart, clear of the finger and of the mark being read. On a
      // mouse it behaves as before.
      triggerOn: L.tapTip ? 'click' : 'mousemove|mouseout',
      position: L.tapTip ? function (pt, params, dom, rect, size) {
        var x = Math.round((size.viewSize[0] - size.contentSize[0]) / 2);
        return [Math.max(4, x), 4];
      } : undefined,
      axisPointer: opts.trigger === 'axis' ? { type: 'line' } : undefined,
      formatter: opts.formatter
    };
  }

  /** A horizontal bar chart, laid out for the width it actually has. */
  function barChart(id, opts) {
    var host = el(id), L = layout(host);
    var rows = opts.rows.slice();
    // A three-line category label on the topmost row overflows above the
    // plot and is clipped. Give it the room rather than shortening the label.
    var top = titleTop(L.w, opts.finding, opts.subtitle) +
              (opts.showN && L.narrow ? 24 : 0);
    // Two-line category labels need taller rows or the second line of one
    // label crowds the bar below it.
    // showN appends the "(n=...)" line further down, in the yAxis mapping,
    // so testing r.label alone reported single-line for Chart 4 and its
    // category labels collided into each other.
    var twoLine = !!opts.showN ||
                  rows.some(function (r) { return r.label.indexOf('\n') >= 0; });
    host.style.height =
      (opts.baseHeight + (L.narrow ? rows.length * 16 : 0) +
       (twoLine ? rows.length * 14 : 0) + Math.max(0, top - 106)) + 'px';
    var ch = echarts.init(host, 'cascadia');
    ch.setOption({
      title: cascadiaTitle(opts.finding, opts.subtitle, { width: L.w - 14 }),
      grid: { left: 8, right: L.gridRight, bottom: 8, top: top,
              containLabel: true },
      // Rule 5.5 drop order, step 3: as the chart narrows, thin the tick
      // density — never rotate. At 320 px the default tick count collided
      // into an unreadable run of digits. The axis UNITS are never dropped,
      // so nameGap grows to keep them clear of the thinned ticks.
      xAxis: { type: 'value', name: opts.units, nameLocation: 'middle',
               nameGap: L.narrow ? 38 : 30, min: 0,
               splitNumber: L.narrow ? 3 : 5,
               axisLabel: { formatter: function (v) {
                 // Declared abbreviation, narrow widths only: 250000 -> 250k.
                 if (L.narrow && v >= 1000) return (v / 1000) + 'k';
                 return nf(v);
               } } },
      yAxis: { type: 'category', inverse: !!opts.inverse,
               data: rows.map(function (r) {
                 var base = L.abbrev(r.label);
                 return opts.showN ? base + '\n(n=' + nf(r.n) + ')' : base;
               }),
               // interval:0 forces EVERY category label to render. ECharts
               // drops labels it thinks would collide, and with two-line
               // labels it silently dropped the first and last categories --
               // two bars with no name against them, which reads as a chart
               // that lost its data rather than one that lost its labels.
               axisLabel: { width: L.labelWidth, overflow: 'break',
                            lineHeight: 15, verticalAlign: 'middle',
                            interval: 0, margin: 10 } },
      tooltip: tip(L, {
        trigger: 'item',
        formatter: function (p) {
          var r = rows[p.dataIndex];
          return (opts.tooltip ? opts.tooltip(r) : r.label + ': ' + nf(r.value));
        }
      }),
      series: [{
        type: 'bar',
        data: rows.map(function (r) {
          if (!opts.colorFor) return r.value;
          var hue = opts.colorFor(r);
          // Rule 2.3.7 — the mark keeps the palette value, the label takes
          // that hue's text ink. textInkFor does the mapping so no module
          // re-derives it.
          return { value: r.value, itemStyle: { color: hue },
                   label: { color: CASCADIA.textInkFor(hue) } };
        }),
        itemStyle: { color: C.evergreen },
        label: { show: !opts.range, position: 'right', fontFamily: SANS,
                 fontSize: 12, color: INK.evergreen,
                 formatter: function (p) {
                   return opts.valueLabel(rows[p.dataIndex]);
                 } }
      }].concat(!opts.range ? [] : [{
        // The value label, carried past the far end of the whisker so it sits
        // clear of every mark.
        type: 'scatter', symbolSize: 0, silent: true,
        data: rows.map(function (r, i) { return [r.p75, i]; }),
        label: { show: true, position: 'right', distance: 8, fontFamily: SANS,
                 fontSize: 12, color: INK.evergreen,
                 formatter: function (p) {
                   return opts.valueLabel(rows[p.dataIndex]);
                 } }
      }, {
        // Rule 4.5 — uncertainty encoded, not asserted away. Two seats asked
        // for a spread: "no variance or spread measure - an IQR, a range -
        // beyond the single median dot per category". The quartiles were in
        // the measure and the table all along; they were not on the canvas.
        // Drawn as a whisker, so the channel is shape and it survives
        // grayscale.
        type: 'custom', silent: true,
        renderItem: function (params, api) {
          var i = api.value(0);
          var r = rows[i];
          if (!r || r.p25 == null) return null;
          var a = api.coord([r.p25, i]), c2 = api.coord([r.p75, i]);
          var cap = Math.max(6, api.size([0, 1])[1] * 0.28);
          var st = { stroke: C.basalt, lineWidth: 1.5, fill: null };
          return { type: 'group', children: [
            { type: 'line', shape: { x1: a[0], y1: a[1], x2: c2[0], y2: c2[1] }, style: st },
            { type: 'line', shape: { x1: a[0], y1: a[1] - cap, x2: a[0], y2: a[1] + cap }, style: st },
            { type: 'line', shape: { x1: c2[0], y1: c2[1] - cap, x2: c2[0], y2: c2[1] + cap }, style: st }
          ] };
        },
        encode: { x: [1, 2], y: 0 },
        data: rows.map(function (r, i) { return [i, r.p25, r.p75]; })
      }])
    });
    cascadiaResize(host, ch);
    cascadiaProvenance(host, { source: SOURCE, asOf: ASOF, flags: opts.flags });
    el('sum-' + id).textContent = opts.summary;
    cascadiaAccessible(host, { label: opts.ariaLabel, summaryId: 'sum-' + id,
                               tableId: 'tbl-' + id });
    return ch;
  }

  /* ---------------- Chart 1 · the decomposition ---------------- */
  (function () {
    var host = el('c1'), L = layout(host), d = D.c1;
    var c1Finding = 'Seven rules separate a nonsense answer from a defensible one — and one of them moves it ' +
      nf(Math.round(Math.abs(d.dominant.delta))) + ' days';
    var c1Sub = 'Days from filing to termination across ' + nf(D.c1.population) +
      ' closed federal civil contract matters. Each bar is one governance rule applied to the same query. Zero is on the axis because the ungoverned answer is negative.';
    var c1Top = titleTop(L.w, c1Finding, c1Sub);
    host.style.height = ((L.narrow ? 470 : 380) + c1Top) + 'px';
    var ch = echarts.init(host, 'cascadia');

    // Each bar is an explicit [from, to] span. A stacked-bar waterfall does
    // not survive a value that crosses zero: ECharts stacks positive and
    // negative values into SEPARATE stacks, so the opening bar rendered on
    // the wrong side of the axis. A custom series draws the span it is given.
    var cats = ['The obvious query'], spans = [];
    spans.push({ from: 0, to: d.start, delta: d.start, anchor: true });
    var running = d.start;
    d.deltas.forEach(function (s) {
      cats.push(s.n + '. ' + L.abbrev(s.label));
      var to = Math.round((running + s.delta) * 10) / 10;
      spans.push({ from: running, to: to, delta: s.delta });
      running = to;
    });
    cats.push('The governed answer');
    spans.push({ from: 0, to: d.end, delta: d.end, anchor: true });

    // Round bounds, with room at both ends MEASURED from the widest value
    // label rather than guessed. A fixed pad was right at 1040 px and wrong
    // at ~630 px, where the narrower plot meant the same label needed more
    // data-units of room and the labels landed back on top of their bars.
    _m.font = '12px ' + SANS;
    var widestLabel = 0;
    spans.forEach(function (sp) {
      var t = sp.anchor ? String(sp.to) : (sp.delta > 0 ? '+' : '') + sp.delta;
      widestLabel = Math.max(widestLabel, _m.measureText(t).width);
    });
    // Measured against the real ECharts grid rect, not estimated. The old
    // expression returned 146 px at a 320 px viewport where the grid is
    // actually 103 -- 42% too generous. Because the padding below is
    // proportional to 1/plotPx, an over-estimated plot UNDER-reserves room,
    // which is the original reason labels landed on their bars.
    var plotPx = Math.max(60, L.w - L.labelWidth - 15 - L.gridRight);
    // The axis must cover EVERY span endpoint, not just the first and last
    // answers. The running total peaks at 319.8 after step 4 and then falls
    // back to 208, so bounds taken from start and end alone cut the axis at
    // 300: three bars ran past the frame and ECharts dropped their labels
    // because the points sat outside the range. K1 catches a series leaving
    // the frame, and this is how one does it quietly.
    var pts = [0];
    spans.forEach(function (sp) { pts.push(sp.from, sp.to); });
    var dmin = Math.min.apply(null, pts), dmax = Math.max.apply(null, pts);
    // Reserving room for a label is a FIXED-POINT problem and the first
    // version solved it once, which is why 320 px still collided after the
    // position fix. Padding the axis widens its range, which shrinks
    // pixels-per-unit, which shrinks the very gap the padding just bought.
    // Solving  p * plotPx >= K * (R + 2p)  for p closes the loop:
    //
    //     p >= K * R / (plotPx - 2K)
    //
    // 2K >= plotPx means no padding can ever fit a label at both ends -- the
    // plot is simply too narrow. Inside-the-bar placement is the usual
    // waterfall answer and is NOT available here: paper on madrona measures
    // 4.31:1 and 12 px text needs 4.5:1, so it would trade a collision for a
    // contrast failure. The label column yields instead; see layout().
    var K = widestLabel + 16;
    var R = dmax - dmin;
    // Can a label fit OUTSIDE the far end of a bar at both ends at all? It
    // needs K px at each end of a plotPx-wide plot, so below 2K there is no
    // solution at any padding -- at a 320 px viewport that is 114 px wanted
    // in a 103 px plot. The 1.2 is headroom: at exactly 2K the data would be
    // squeezed to nothing and the waterfall would stop showing its shape.
    var labelsFit = plotPx > 2 * K * 1.2;
    var pad = labelsFit ? (K * R) / (plotPx - 2 * K)
                        : R * 0.06;
    var lo = Math.floor((dmin - pad) / 100) * 100;
    var hi = Math.ceil((dmax + pad) / 100) * 100;
    var domIdx = 0;
    spans.forEach(function (s, i) { if (s.delta === d.dominant.delta) domIdx = i; });

    ch.setOption({
      title: cascadiaTitle(c1Finding, c1Sub, { width: L.w - 14 }),
      grid: { left: 8, right: L.narrow ? 40 : 92, bottom: 8, top: c1Top,
              containLabel: true },
      xAxis: { type: 'value', name: 'days', nameLocation: 'middle',
               nameGap: L.narrow ? 36 : 30, splitNumber: L.narrow ? 3 : 6,
               min: Math.round(lo), max: Math.round(hi) },
      yAxis: { type: 'category', data: cats, inverse: true,
               axisLabel: { width: L.labelWidth, overflow: 'break',
                            lineHeight: 15 } },
      tooltip: tip(L, {
        trigger: 'axis',
        formatter: function (ps) {
          var i = ps && ps.length ? ps[0].dataIndex : 0;
          var sp = spans[i];
          if (!sp) return '';
          return cats[i] + '<br>' +
            (sp.anchor ? 'answer: ' + sp.to + ' days'
                       : (sp.delta > 0 ? '+' : '') + sp.delta +
                         ' days → ' + sp.to + ' days');
        }
      }),
      series: [{
        type: 'custom',
        renderItem: function (params, api) {
          var i = api.value(0);
          var s = spans[i];
          var a = api.coord([s.from, i]), b = api.coord([s.to, i]);
          var size = api.size([0, 1]);
          var bh = Math.max(10, size[1] * 0.55);
          var x = Math.min(a[0], b[0]);
          // A sub-day step is a real step and is not hidden. Below ~1.5px it
          // is drawn as a minimum-width tick so the row carries a mark.
          var wpx = Math.max(1.5, Math.abs(b[0] - a[0]));
          return {
            type: 'rect',
            shape: { x: x, y: a[1] - bh / 2, width: wpx, height: bh },
            style: { fill: s.delta >= 0 ? C.evergreen : C.madrona }
          };
        },
        encode: { x: [1, 2], y: 0 },
        data: spans.map(function (s, i) { return [i, s.from, s.to]; })
      }, {
        // Value labels as their own scatter layer, so each sits OUTSIDE its
        // bar's far end rather than printed over a rect that may be 1.5 px
        // wide. label.position takes a string, not a callback, so the
        // position and ink are set per datum — a callback here silently
        // fell back to a default and printed every label over its bar.
        type: 'scatter', symbolSize: 0,
        data: spans.map(function (s, i) {
          var rightward = s.to >= s.from;
          return {
            value: [s.to, i],
            label: {
              // Rule 5.5 drop order: where the geometry cannot seat a label
              // outside its bar, the label is DROPPED rather than printed
              // over the mark or squeezed inside it. Inside is not available
              // -- paper on madrona measures 4.31:1 and 12 px text needs
              // 4.5:1. The values stay reachable: the tap/hover readout
              // carries them, and the data table always has.
              show: labelsFit, fontFamily: SANS, fontSize: 12,
              // Always OUTSIDE the bar's far end. A narrow-width special
              // case used 'top', which anchors to the data point at the
              // ROW'S VERTICAL CENTRE rather than to the top of the rect --
              // so "7px above the point" was 7px into a bar whose half
              // height is ~26px, and every leftward label was bisected by
              // its own bar. The axis already reserves room for the widest
              // label (see `pad`), so 'left' fits at every width.
              position: rightward ? 'right' : 'left',
              distance: 7,
              color: s.delta >= 0 ? INK.evergreen : INK.madrona,
              formatter: s.anchor ? String(s.to)
                                  : (s.delta > 0 ? '+' : '') + s.delta
            }
          };
        })
      }].concat(L.w < 900 ? [] : [{
        // Rule 3.4 — the finding is annotated on the mark that carries it.
        // Anchored in the band beside the sub-day steps, whose only marks sit
        // hard against the left edge, so no mark is overdrawn (K3).
        //
        // Below 900 px there is no such free space: the prose leaves the plot
        // and appears beneath it instead (Rule 5.5 drop order, step 4). It is
        // one or the other, never both — an earlier version rendered the
        // in-plot annotation at every width AND the note below it, which
        // printed the same sentence twice and overlapped a bar at 320 px.
        type: 'scatter', symbolSize: 0, data: [],
        markPoint: cascadiaAnnotation(
          'Pending matters carry a termination date of 01/01/1900 —\na well-formed date that is not a termination.',
          { coord: [Math.round(lo * 0.30), Math.max(0, domIdx - 1)],
            color: C.evergreen, position: 'top', distance: 26, width: 330,
            container: host })
      }])
    });
    cascadiaResize(host, ch);
    cascadiaProvenance(host, { source: SOURCE, asOf: ASOF,
      flags: 'every step re-derived from the frozen file; no step omitted or rescaled' });
    var c1note = el('c1-note');
    if (c1note) {
      var c1Out = L.w < 900;
      c1note.textContent = c1Out
        ? ('Step 4 is the one that moves the answer: pending matters carry a termination date of 01/01/1900 — a well-formed date that is not a termination.' +
           // Say where the numbers went. A value that is silently absent
           // reads as a value that does not exist.
           (labelsFit ? '' : ' At this width the step values are in the data table below, or tap a bar to read one.'))
        : '';
      c1note.style.display = c1Out ? 'block' : 'none';
    }

    el('sum-c1').textContent =
      'Waterfall, read top to bottom. The ungoverned answer of ' + d.start +
      ' days rises to ' + d.end + ' days as seven rules are applied. The shape is two long ' +
      'bars and five almost invisible ones: step ' + d.dominant.n + ', ' + d.dominant.label +
      ', moves the answer ' + Math.abs(d.dominant.delta) + ' days on its own, while ' +
      d.smallCount + ' steps move it ' + Math.abs(d.smallSum) +
      ' days between them and are drawn at true scale rather than dropped or rescaled.';
    cascadiaAccessible(host, {
      label: 'Waterfall chart: the effect of each governance rule on the answer, in days.',
      summaryId: 'sum-c1', tableId: 'tbl-c1' });
  })();

  /* ---------------- Chart 2 · the trend trap ---------------- */
  (function () {
    var host = el('c2'), L = layout(host), d = D.c2;
    var lo = Math.min.apply(null, d.governed), hi = Math.max.apply(null, d.ungoverned);
    // Rule 2.1 REVERSED: the title makes a DIFFERENCE claim ("wrong by 1,062
    // days"), so truncation is permitted. The floor is set below the lowest
    // point rather than at zero, which is what lets Rule 1.3's banking work.
    var yMin = Math.floor((lo - 30) / 25) * 25;
    // K3: reserved headroom. The annotation goes in space the axis makes for
    // it, never over a mark.
    // One axis for every width. Reserving headroom only on desktop made the
    // phone version's gridlines 50 days apart where desktop's were 100, and a
    // seat reported the two lines looking "visually farther apart" as a
    // result. A chart that changes its scale by viewport is two charts.
    var yMax = Math.ceil((hi + 120) / 25) * 25;
    var c2Finding = 'Both trends agree that contract matters are getting slower — and one of them is built on an answer that is wrong by ' +
      nf(Math.round(Math.abs(D.c1.dominant.delta))) + ' days';
    var c2Sub = 'Days from filing to termination by statistical year, ' + d.years[0] + '–' +
      d.years[d.years.length - 1] + '. Same file, same slice, two methods. Axis truncated below ' +
      yMin + ' days; the claim is a difference, not a ratio.';
    var c2Top = titleTop(L.w, c2Finding, c2Sub);
    // Rule 1.3 banking sizes the PLOT; the title block is added on top of it
    // rather than taken out of it, or the banked slope is not what ships.
    var h = cascadiaBankedHeight(d.governed, L.w, { min: 240, max: 460 });
    host.style.height = ((h || 320) + c2Top) + 'px';
    var ch = echarts.init(host, 'cascadia');

    var annotation =
      'The broken records are invisible here: 32,767 pending cases carry statistical year 2099 and fall off the end of this axis. They are why the ungoverned headline answer is negative.';

    ch.setOption({
      title: cascadiaTitle(c2Finding, c2Sub, { width: L.w - 14 }),
      grid: { left: 8, right: L.narrow ? 96 : 150, bottom: 8, top: c2Top,
              containLabel: true },
      // One hover reports BOTH series for the year under the pointer, which
      // is the comparison the chart is making. Gone below 769 px per 5.5.
      tooltip: tip(L, {
        trigger: 'axis',
        formatter: function (ps) {
          if (!ps || !ps.length) return '';
          var out = 'Statistical year ' + ps[0].axisValue;
          ps.forEach(function (q) {
            out += '<br>' + q.seriesName + ': ' + q.data + ' days';
          });
          return out;
        }
      }),
      xAxis: { type: 'category', data: d.years, boundaryGap: false,
               axisLabel: { interval: L.narrow ? 7 : 4 } },
      yAxis: { type: 'value', name: 'days', nameLocation: 'end', nameGap: 12,
               nameTextStyle: { align: 'left' }, min: yMin, max: yMax },
      series: [
        { name: 'Ungoverned mean', type: 'line', data: d.ungoverned,
          lineStyle: { color: C.madrona, type: 'dashed', width: 2 },
          itemStyle: { color: C.madrona }, symbol: 'circle', symbolSize: 4,
          // Rule 5.5: the direct label on a series is NEVER dropped. Two panel
          // seats independently reported that at phone width the lines "just
          // end with no text" and they could not tell which was which.
          endLabel: { show: true, fontFamily: SANS, fontSize: 12,
                      color: INK.madrona,
                      formatter: L.narrow ? 'mean\n{c} d'
                                          : 'Ungoverned mean\n{c} days' } },
        { name: 'Governed median', type: 'line', data: d.governed,
          lineStyle: { color: C.evergreen, width: 2.5 },
          itemStyle: { color: C.evergreen }, symbol: 'circle', symbolSize: 4,
          endLabel: { show: true, fontFamily: SANS, fontSize: 12,
                      color: INK.evergreen,
                      formatter: L.narrow ? 'median\n{c} d'
                                          : 'Governed median\n{c} days' } }
      ],
      legend: { show: false }
    });

    if (!L.narrow) {
      // Anchored in the reserved headroom, above both series.
      ch.setOption({ series: [{}, { markPoint: cascadiaAnnotation(
        '32,767 pending cases carry statistical year 2099 and fall off\nthis axis. They are why the ungoverned headline answer\nis negative — the chart above shows it.',
        { coord: [Math.round(d.years.length * 0.42), yMax - 22],
          color: C.evergreen, position: 'bottom', distance: 4, width: 340,
          container: host }) }] });
    }

    cascadiaResize(host, ch);
    cascadiaProvenance(host, { source: SOURCE, asOf: ASOF,
      flags: 'pending records excluded from the governed series only' });

    var narrowNote = el('c2-note');
    if (narrowNote) {
      // Rule 5.5 drop order step 4: annotation prose moves OUT of the plot at
      // narrow widths rather than being deleted or printed over the data.
      narrowNote.textContent = L.narrow ? annotation : '';
      narrowNote.style.display = L.narrow ? 'block' : 'none';
    }
    // Direct labels never drop (5.5). At narrow widths they move out of the
    // plot and into the summary's first sentence instead of the line end.
    var lead = L.narrow
      ? 'Ungoverned mean, dashed, ends at ' + d.ungoverned[d.ungoverned.length - 1] +
        ' days; governed median, solid, ends at ' + d.governed[d.governed.length - 1] + ' days. '
      : '';
    el('sum-c2').textContent = lead +
      'Two lines on one value axis, both in days, ' + d.years[0] + ' to ' +
      d.years[d.years.length - 1] + '. Both rise. The ungoverned mean runs from ' +
      d.ungoverned[0] + ' to ' + d.ungoverned[d.ungoverned.length - 1] +
      ' days; the governed median runs from ' + d.governed[0] + ' to ' +
      d.governed[d.governed.length - 1] + ' days. The lines stay roughly parallel and never ' +
      'cross. The agreement is an accident: the records that make the headline figure wrong ' +
      'carry a sentinel statistical year of 2099 and fall outside this axis entirely.';
    cascadiaAccessible(host, {
      label: 'Line chart: days to termination by year, governed and ungoverned methods compared.',
      summaryId: 'sum-c2', tableId: 'tbl-c2' });
    cascadiaNavigator(host, {
      chart: ch,
      label: 'Days to termination by statistical year, two series.',
      series: [
        { name: 'Ungoverned mean', points: d.years.map(function (y, i) {
            return { label: 'Statistical year ' + y, value: d.ungoverned[i] + ' days',
                     seriesIndex: 0, dataIndex: i }; }) },
        { name: 'Governed median', points: d.years.map(function (y, i) {
            return { label: 'Statistical year ' + y, value: d.governed[i] + ' days',
                     seriesIndex: 1, dataIndex: i }; }) }
      ]
    });
  })();

  /* ---------------- Chart 3 · procedural progress ---------------- */
  (function () {
    var d = D.c3;
    var tot = d.reduce(function (a, r) { return a + r.n; }, 0);
    var before = d.filter(function (r) { return r.group === 'before issue joined'; })
                  .reduce(function (a, r) { return a + r.n; }, 0);
    var pct = Math.round(1000 * before / tot) / 10;
    var top = d[0];
    barChart('c3', {
      // Every label is exactly two lines: the act, then its issue-joined
      // group in parentheses. The qualified single-line form wrapped at
      // different points per category -- "issue" fell to a second line on
      // some rows and not others -- which made a ranked list hard to scan.
      // The group is a DECLARED abbreviation of the codebook's own wording
      // (which reads "after ISSUED joined" -- a typo in the source, not here).
      rows: d.slice().sort(function (a, b) { return a.n - b.n; })
             .map(function (r) {
               var g = r.group.indexOf('before') === 0 ? 'before issue' : 'after issue';
               return { label: r.description + '\n(' + g + ')',
                        n: r.n, value: r.n, pct: r.pct, median: r.median,
                        before: r.group.indexOf('before') === 0 };
             }),
      baseHeight: 440, units: 'matters',
      finding: pct + '% of contract matters end before the issue is even joined',
      subtitle: 'All federal civil contract filings, not one department’s portfolio. Green bars are the four categories that fall before issue was joined; blue are after. “Other” is the codebook’s own residual category and its contents are not further specified by the source.',
      // Four seats independently reported that the title's 43% "is not drawn
      // anywhere on the chart" — bars carried raw counts and the two groups the
      // claim compares were not visually separated. Both are now on the canvas.
      // The parenthetical stays on every label, so the split also survives
      // grayscale on the text channel.
      colorFor: function (r) { return r.before ? C.evergreen : C.glacier; },
      valueLabel: function (r) {
        return nf(r.value) + '   ' +
               (r.pct < 0.05 ? '<0.1' : r.pct.toFixed(1)) + '%';
      },
      tooltip: function (r) {
        return r.label.replace('\n', ' ') + '<br>' + nf(r.n) + ' matters · ' +
               r.pct + '%' + (r.median ? ' · median ' + r.median + ' days' : '');
      },
      flags: 'certified measure M-03; codes qualified by issue-joined group',
      summary: 'Sorted bar chart. The shape is a long tail: the largest category, ' +
        top.description + ' (' +
        (top.group.indexOf('before') === 0 ? 'before issue' : 'after issue') +
        '), holds ' + nf(top.n) + ' matters (' + top.pct +
        '%), and the smallest hold a few thousand each. The four categories that sit before ' +
        'the issue was joined account for ' + nf(before) + ' matters, ' + pct +
        '% of all closed contract matters.',
      ariaLabel: 'Sorted bar chart: closed contract matters by procedural progress at termination.'
    });
  })();

  /* ---------------- Chart 4 · time to termination ---------------- */
  (function () {
    var d = D.c4, minN = Math.min.apply(null, d.map(function (r) { return r.n; }));
    barChart('c4', {
      rows: d.map(function (r) {
              return { label: r.label, n: r.n, value: r.median,
                       p25: r.p25, p75: r.p75 };
            }),
      inverse: true, showN: true, baseHeight: 430, units: 'days', range: true,
      finding: 'Median time to resolve runs from ' + d[0].median + ' to ' +
               d[d.length - 1].median + ' days depending on the kind of contract dispute',
      subtitle: (layout(el('c4')).narrow
        ? 'Median days from filing to termination, closed contract matters, by nature of suit. Category size is on every bar; medians over very different populations are not the same claim. The whisker is the 25th to 75th percentile.'
        : 'Median days from filing to termination, closed contract matters, by nature of suit. Category size is stated on every bar because a median over ' +
          nf(minN) + ' matters and one over ' + nf(d[d.length - 1].n) +
          ' are not the same claim. The whisker on each bar is the 25th to 75th percentile.'),
      valueLabel: function (r) { return r.value + ' d'; },
      tooltip: function (r) {
        return r.label + '<br>median ' + r.value + ' days · 25th ' + r.p25 +
               ' · 75th ' + r.p75 + '<br>' + nf(r.n) + ' closed matters';
      },
      flags: 'certified measure M-01; median, exact over the full closed population',
      summary: 'Sorted bar chart, fastest at the top. The spread is roughly threefold: ' +
        d[0].label + ' resolves in a median ' + d[0].median + ' days over ' + nf(d[0].n) +
        ' matters, while ' + d[d.length - 1].label + ' takes ' + d[d.length - 1].median +
        ' days over ' + nf(d[d.length - 1].n) + '. Every category holds at least ' + nf(minN) +
        ' closed matters, and each median is exact over that whole population rather than sampled.',
      ariaLabel: 'Sorted bar chart: median days from filing to termination by nature of suit.'
    });
  })();

  /* ---------------- Chart 5 · disposition mix ---------------- */
  (function () {
    var d = D.c5;
    var settled = d.filter(function (r) { return r.label === 'settled'; })[0];
    var jury = d.filter(function (r) { return r.label === 'jury verdict'; })[0];
    var juryRank = d.slice().sort(function (a, b) { return b.n - a.n; })
                    .findIndex(function (r) { return r.label === 'jury verdict'; }) + 1;
    // Two dispositions carry the same description in the codebook's code
    // list -- code 14 is a dismissal "other", code 17 is a judgment "other".
    // Same defect class as the procedural-progress codes, one field over.
    // dim_disp does not carry the group, so the chart disambiguates by the
    // code, which IS in the certified measure. Recorded as a finding rather
    // than repaired in the data layer from here.
    var dupes = {};
    d.forEach(function (r) { dupes[r.label] = (dupes[r.label] || 0) + 1; });
    barChart('c5', {
      rows: d.slice().sort(function (a, b) { return a.n - b.n; })
             .map(function (r) {
               return { label: dupes[r.label] > 1
                          ? r.label + ' (code ' + r.code + ')' : r.label,
                        n: r.n, value: r.pct };
             }),
      baseHeight: 480, units: '% of closed matters',
      finding: settled.pct + '% of contract matters settle; ' + jury.pct +
               '% reach a jury verdict',
      subtitle: 'Closed contract matters by the manner in which the court disposed of the case. The disposition is the court’s characterisation of the ending, not the department’s.',
      // The title makes a percentage claim, so the bars carry percentages and
      // the counts move to the tooltip -- Rule 4.4 names the tooltip as the
      // home for full precision. The share is already a column in the
      // certified measure; nothing new is derived here.
      // One decimal throughout, and never a bare "0%" for a category that
      // is not empty: 178 matters is 0.013%, and printing that as 0% states
      // something the data does not say.
      valueLabel: function (r) {
        return r.value < 0.05 ? '<0.1%' : r.value.toFixed(1) + '%';
      },
      tooltip: function (r) { return r.label + '<br>' + nf(r.n) +
                                     ' matters · ' + r.value + '%'; },
      flags: 'certified measure M-02; transfers and remands are continuations, not outcomes',
      summary: 'Sorted bar chart. The shape is dominated by two bars: settlement at ' +
        nf(settled.n) + ' matters (' + settled.pct + '%) and voluntary dismissal below it, ' +
        'with a long tail of smaller dispositions. A jury verdict, at ' + nf(jury.n) +
        ' matters, is ' + jury.pct + '% — ' + juryRank + 'th of ' + d.length +
        ' dispositions, with ' + (d.length - juryRank) + ' smaller ones below it.',
      ariaLabel: 'Sorted bar chart: closed contract matters by disposition.'
    });
  })();
})();
