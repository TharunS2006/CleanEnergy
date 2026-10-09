/* Small hand-written SVG charts for CloudPulse. No dependencies. */
(() => {
  "use strict";

  const tipEl = () => document.getElementById("tooltip");
  const tip = {
    show(html, clientX, clientY) {
      const el = tipEl();
      el.innerHTML = html;
      el.hidden = false;
      const r = el.getBoundingClientRect();
      let x = clientX + 14;
      let y = clientY - r.height - 12;
      if (x + r.width > window.innerWidth - 8) x = clientX - r.width - 14;
      if (y < 8) y = clientY + 16;
      el.style.left = `${Math.max(8, x)}px`;
      el.style.top = `${y}px`;
    },
    hide() { tipEl().hidden = true; },
  };

  function niceMax(v) {
    if (!(v > 0)) return 1;
    const p = Math.pow(10, Math.floor(Math.log10(v)));
    for (const m of [1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]) if (m * p >= v * 1.04) return m * p;
    return 10 * p;
  }

  const roundTop = (x, y, w, h, r) => {
    r = Math.min(r, w / 2, h);
    return `M${x},${y + h}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h}Z`;
  };

  /**
   * Stacked (or single) daily bars.
   * opts: days [{date, values:{key:amount}}], groups [{key,label,color}],
   *       fmt(n), fmtAxis(n), fmtDate(iso), fmtDateLong(iso),
   *       anomalies Set<date>, ref {value,label}, height, highlight date, marker {date,label}
   */
  function bars(host, opts) {
    if (!host || !host.isConnected) return;
    const { days, groups } = opts;
    const W = Math.max(300, Math.round(host.clientWidth || 700));
    const H = opts.height || 240;
    const pad = { l: 52, r: 8, t: 18, b: 28 };
    const iw = W - pad.l - pad.r;
    const ih = H - pad.t - pad.b;
    const totals = days.map((d) => groups.reduce((s, g) => s + (d.values[g.key] || 0), 0));
    const max = niceMax(Math.max(...totals, opts.ref ? opts.ref.value : 0));
    const slot = iw / days.length;
    const bw = Math.max(2, Math.min(24, slot * 0.64));
    const y = (v) => pad.t + ih - (v / max) * ih;

    let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${opts.label || "Daily spend"}">`;
    for (let i = 0; i <= 4; i++) {
      const v = (max / 4) * i;
      s += `<line class="grid-line" x1="${pad.l}" x2="${W - pad.r}" y1="${y(v)}" y2="${y(v)}"/>`;
      if (i % 2 === 0) s += `<text class="axis" x="${pad.l - 8}" y="${y(v) + 4}" text-anchor="end">${opts.fmtAxis(v)}</text>`;
    }
    const every = Math.ceil(days.length / (W < 560 ? 4 : W < 900 ? 6 : 8));
    days.forEach((d, i) => {
      const cx = pad.l + slot * i + slot / 2;
      const x = cx - bw / 2;
      let base = pad.t + ih;
      const present = groups.filter((g) => (d.values[g.key] || 0) > 0);
      present.forEach((g, gi) => {
        const h = ((d.values[g.key] || 0) / max) * ih;
        if (h < 0.3) return;
        const top = base - h;
        const isTop = gi === present.length - 1;
        const dim = opts.highlight && opts.highlight !== d.date ? " dimmed" : "";
        s += isTop
          ? `<path class="seg-rect${dim}" data-i="${i}" style="fill:${g.color}" d="${roundTop(x, top, bw, h, 4)}"/>`
          : `<rect class="seg-rect${dim}" data-i="${i}" style="fill:${g.color}" x="${x}" y="${top}" width="${bw}" height="${h}"/>`;
        base = top;
      });
      if (opts.anomalies && opts.anomalies.has(d.date)) {
        s += `<circle class="anomaly-dot" cx="${cx}" cy="${y(totals[i]) - 9}" r="4"/>`;
      }
      if (i % every === 0) s += `<text class="axis" x="${cx}" y="${H - 8}" text-anchor="middle">${opts.fmtDate(d.date)}</text>`;
      s += `<rect class="hit" data-i="${i}" x="${pad.l + slot * i}" y="${pad.t}" width="${slot}" height="${ih}"/>`;
    });
    if (opts.marker) {
      const mi = days.findIndex((d) => d.date >= opts.marker.date);
      if (mi >= 0) {
        const mx = pad.l + slot * mi;
        s += `<line class="breach-line marker" x1="${mx}" x2="${mx}" y1="${pad.t - 6}" y2="${pad.t + ih}"/>`;
        const rightSide = mi > days.length * 0.6;
        s += `<text class="axis marker-label" x="${mx + (rightSide ? -4 : 4)}" y="${pad.t - 8}" text-anchor="${rightSide ? "end" : "start"}">${esc(opts.marker.label)}</text>`;
      }
    }
    if (opts.ref && opts.ref.value > 0) {
      const ry = y(opts.ref.value);
      s += `<line class="ref-line" x1="${pad.l}" x2="${W - pad.r}" y1="${ry}" y2="${ry}"/>`;
    }
    s += "</svg>";
    host.innerHTML = s;
    host.classList.add("chart");

    const svg = host.querySelector("svg");
    const setDim = (i) => svg.querySelectorAll(".seg-rect").forEach((el) => {
      el.classList.toggle("dimmed", i != null && Number(el.dataset.i) !== i);
    });
    svg.onpointermove = (e) => {
      const t = e.target.closest("[data-i]");
      if (!t) { tip.hide(); setDim(null); return; }
      const i = Number(t.dataset.i);
      const d = days[i];
      setDim(i);
      const rows = groups
        .filter((g) => (d.values[g.key] || 0) > 0)
        .slice().reverse()
        .map((g) => `<div class="row"><span><i class="swatch" style="background:${g.color}"></i>${esc(g.label)}</span><b>${opts.fmt(d.values[g.key])}</b></div>`)
        .join("");
      const note = opts.anomalies && opts.anomalies.has(d.date) ? `<div class="note">Unusual spike</div>` : "";
      tip.show(
        `<h4>${opts.fmtDateLong(d.date)}</h4>${groups.length > 1 ? rows : ""}` +
        `<div class="row ${groups.length > 1 ? "total" : ""}"><span>Total</span><b>${opts.fmt(totals[i])}</b></div>${note}`,
        e.clientX, e.clientY
      );
    };
    svg.onpointerleave = () => { tip.hide(); setDim(null); };
    if (opts.onClick) {
      svg.style.cursor = "pointer";
      svg.onclick = (e) => { const t = e.target.closest("[data-i]"); if (t) opts.onClick(days[Number(t.dataset.i)]); };
    }
  }

  /**
   * Month so far plus forecast.
   * opts: path [{date, actual, forecast}] (cumulative), budget, low, high,
   *       breach (iso date), fmt, fmtAxis, fmtDate, fmtDateLong, height
   */
  function cumulative(host, opts) {
    if (!host || !host.isConnected) return;
    const pts = opts.path.map((p) => ({ date: p.date, actual: p.actual, forecast: p.forecast }));
    const W = Math.max(300, Math.round(host.clientWidth || 700));
    const H = opts.height || 280;
    const pad = { l: 56, r: 16, t: 20, b: 28 };
    const iw = W - pad.l - pad.r;
    const ih = H - pad.t - pad.b;
    const n = pts.length;
    const known = pts.filter((p) => p.actual != null);
    const future = pts.filter((p) => p.forecast != null);
    const last = known[known.length - 1];
    const endF = future.length ? future[future.length - 1].forecast : null;
    const max = niceMax(Math.max(opts.budget || 0, opts.high || 0, endF || 0, last ? last.actual : 0));
    const x = (i) => pad.l + (n === 1 ? 0 : (i / (n - 1)) * iw);
    const y = (v) => pad.t + ih - (v / max) * ih;
    const idx = (p) => pts.indexOf(p);

    let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(opts.label || "Spend this month with forecast")}">`;
    for (let i = 0; i <= 4; i++) {
      const v = (max / 4) * i;
      s += `<line class="grid-line" x1="${pad.l}" x2="${W - pad.r}" y1="${y(v)}" y2="${y(v)}"/>`;
      s += `<text class="axis" x="${pad.l - 8}" y="${y(v) + 4}" text-anchor="end">${opts.fmtAxis(v)}</text>`;
    }
    const every = Math.ceil(n / (W < 560 ? 4 : 7));
    pts.forEach((p, i) => { if (i % every === 0) s += `<text class="axis" x="${x(i)}" y="${H - 8}" text-anchor="middle">${opts.fmtDate(p.date)}</text>`; });

    // Uncertainty cone: from the last actual point to the low/high range at month end.
    if (last && future.length && opts.low != null && opts.high != null && opts.high > opts.low) {
      const f0 = idx(future[0]);
      const span = Math.max(1, (n - 1) - idx(last));
      const half = (i) => ((opts.high - opts.low) / 2) * Math.sqrt((i - idx(last)) / span);
      const up = future.map((p) => `${x(idx(p))},${y(p.forecast + half(idx(p)))}`);
      const dn = future.slice().reverse().map((p) => `${x(idx(p))},${y(Math.max(0, p.forecast - half(idx(p))))}`);
      s += `<path class="band" d="M${x(idx(last))},${y(last.actual)} L${up.join(" L")} L${dn.join(" L")} Z"/>`;
      void f0;
    }
    if (opts.budget) {
      s += `<line class="budget-flat" x1="${pad.l}" x2="${W - pad.r}" y1="${y(opts.budget)}" y2="${y(opts.budget)}"/>`;
      s += `<text class="axis budget-label" x="${pad.l + 4}" y="${y(opts.budget) - 6}">Budget ${opts.fmtAxis(opts.budget)}</text>`;
    }
    if (known.length) {
      const line = known.map((p, k) => `${k ? "L" : "M"}${x(idx(p))},${y(p.actual)}`).join(" ");
      s += `<path class="line-area" d="${line} L${x(idx(last))},${y(0)} L${x(idx(known[0]))},${y(0)} Z"/>`;
      s += `<path class="line" d="${line}"/>`;
    }
    if (future.length) {
      const start = last ? `M${x(idx(last))},${y(last.actual)} ` : "";
      const fl = future.map((p, k) => `${!start && !k ? "M" : "L"}${x(idx(p))},${y(p.forecast)}`).join(" ");
      s += `<path class="forecast-line" d="${start}${fl}"/>`;
      s += `<circle class="end-dot hollow" cx="${x(n - 1)}" cy="${y(endF)}" r="4"/>`;
    }
    if (opts.breach) {
      const bi = pts.findIndex((p) => p.date === opts.breach);
      if (bi >= 0) {
        s += `<line class="breach-line" x1="${x(bi)}" x2="${x(bi)}" y1="${pad.t}" y2="${pad.t + ih}"/>`;
        const right = bi > n * 0.55;
        s += `<text class="axis breach-label" x="${x(bi) + (right ? -6 : 6)}" y="${pad.t - 6}" text-anchor="${right ? "end" : "start"}">Over budget ${opts.fmtDate(opts.breach)}</text>`;
      }
    }
    if (last) s += `<circle class="end-dot" cx="${x(idx(last))}" cy="${y(last.actual)}" r="5"/>`;
    pts.forEach((p, i) => {
      const w = iw / Math.max(1, n - 1);
      s += `<rect class="hit" data-i="${i}" x="${x(i) - w / 2}" y="${pad.t}" width="${w}" height="${ih}"/>`;
    });
    s += "</svg>";
    host.innerHTML = s;
    host.classList.add("chart");

    const svg = host.querySelector("svg");
    svg.onpointermove = (e) => {
      const t = e.target.closest("[data-i]");
      if (!t) return tip.hide();
      const i = Number(t.dataset.i);
      const p = pts[i];
      const prev = i > 0 ? pts[i - 1] : null;
      const cur = p.actual != null ? p.actual : p.forecast;
      const before = prev ? (prev.actual != null ? prev.actual : prev.forecast) : 0;
      tip.show(
        `<h4>${opts.fmtDateLong(p.date)}</h4>` +
        (p.actual != null
          ? `<div class="row"><span>Spent so far</span><b>${opts.fmt(p.actual)}</b></div><div class="row"><span>That day</span><b>${opts.fmt(cur - before)}</b></div>`
          : `<div class="row"><span>Forecast total</span><b>${opts.fmt(p.forecast)}</b></div><div class="row"><span>Forecast for the day</span><b>${opts.fmt(cur - before)}</b></div>`) +
        (opts.budget ? `<div class="row"><span>Budget left</span><b>${opts.fmt(opts.budget - cur)}</b></div>` : ""),
        e.clientX, e.clientY
      );
    };
    svg.onpointerleave = tip.hide;
  }

  /**
   * Before/after bars for a verified fix.
   * opts: before [{date, amount}], after [{date, amount}], beforeAvg, afterAvg, fmt, fmtAxis, fmtDate, fmtDateLong
   */
  function beforeAfter(host, opts) {
    if (!host || !host.isConnected) return;
    const rows = [...opts.before.map((r) => ({ ...r, side: "before" })), ...opts.after.map((r) => ({ ...r, side: "after" }))];
    const W = Math.max(280, Math.round(host.clientWidth || 440));
    const H = opts.height || 170;
    const pad = { l: 46, r: 10, t: 22, b: 24 };
    const iw = W - pad.l - pad.r, ih = H - pad.t - pad.b;
    const gap = 14;
    const n = rows.length;
    const slot = (iw - gap) / Math.max(1, n);
    const max = niceMax(Math.max(0.0001, ...rows.map((r) => r.amount)));
    const y = (v) => pad.t + ih - (v / max) * ih;
    const xOf = (i) => pad.l + i * slot + (rows[i].side === "after" ? gap : 0);
    const nb = opts.before.length;
    let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Daily cost before and after the fix">`;
    for (let i = 0; i <= 2; i++) {
      const v = (max / 2) * i;
      s += `<line class="grid-line" x1="${pad.l}" x2="${W - pad.r}" y1="${y(v)}" y2="${y(v)}"/>`;
      s += `<text class="axis" x="${pad.l - 6}" y="${y(v) + 4}" text-anchor="end">${opts.fmtAxis(v)}</text>`;
    }
    rows.forEach((r, i) => {
      const bw = Math.max(2, slot * 0.7);
      const h = Math.max(r.amount > 0 ? 2 : 0, pad.t + ih - y(r.amount));
      s += `<path class="ba-${r.side}" d="${roundTop(xOf(i) + (slot - bw) / 2, pad.t + ih - h, bw, h, 2)}"/>`;
      s += `<rect class="hit" data-i="${i}" x="${xOf(i)}" y="${pad.t}" width="${slot}" height="${ih}"/>`;
    });
    const divX = pad.l + nb * slot + gap / 2;
    s += `<line class="ba-divider" x1="${divX}" x2="${divX}" y1="${pad.t - 14}" y2="${pad.t + ih}"/>`;
    s += `<text class="axis" x="${pad.l}" y="${pad.t - 8}">Before · avg ${opts.fmt(opts.beforeAvg)}/day</text>`;
    s += `<text class="axis" x="${divX + gap / 2}" y="${pad.t - 8}">After · avg ${opts.fmt(opts.afterAvg)}/day</text>`;
    if (nb) s += `<line class="ba-avg" x1="${pad.l}" x2="${divX - gap / 2}" y1="${y(opts.beforeAvg)}" y2="${y(opts.beforeAvg)}"/>`;
    if (opts.after.length) s += `<line class="ba-avg" x1="${divX + gap / 2}" x2="${W - pad.r}" y1="${y(opts.afterAvg)}" y2="${y(opts.afterAvg)}"/>`;
    if (n) {
      s += `<text class="axis" x="${xOf(0)}" y="${H - 6}">${opts.fmtDate(rows[0].date)}</text>`;
      s += `<text class="axis" x="${W - pad.r}" y="${H - 6}" text-anchor="end">${opts.fmtDate(rows[n - 1].date)}</text>`;
    }
    s += "</svg>";
    host.innerHTML = s;
    host.classList.add("chart");
    const svg = host.querySelector("svg");
    svg.onpointermove = (e) => {
      const t = e.target.closest("[data-i]");
      if (!t) return tip.hide();
      const r = rows[Number(t.dataset.i)];
      tip.show(`<h4>${opts.fmtDateLong(r.date)}</h4><div class="row"><span>${r.side === "before" ? "Before the fix" : "After the fix"}</span><b>${opts.fmt(r.amount)}</b></div>`, e.clientX, e.clientY);
    };
    svg.onpointerleave = tip.hide;
  }

  /** Tiny inline trend line, no interaction. values: number[] */
  function spark(values, w = 120, h = 28, cls = "") {
    if (!values || values.length < 2) return "";
    const max = Math.max(...values), min = Math.min(0, ...values);
    const span = max - min || 1;
    const pts = values.map((v, i) => `${((i / (values.length - 1)) * (w - 2) + 1).toFixed(1)},${(h - 2 - ((v - min) / span) * (h - 4)).toFixed(1)}`);
    return `<svg class="spark ${cls}" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" aria-hidden="true"><polyline points="${pts.join(" ")}"/></svg>`;
  }

  function esc(v) {
    return String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  window.CPCharts = { bars, cumulative, beforeAfter, spark, tip, esc };
})();
