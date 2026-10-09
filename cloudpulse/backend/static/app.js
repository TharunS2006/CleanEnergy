(() => {
  "use strict";
  const { bars, cumulative, beforeAfter, tip, esc } = window.CPCharts;
  const $ = (s, root = document) => root.querySelector(s);
  const $$ = (s, root = document) => [...root.querySelectorAll(s)];

  // ================================================================ state
  const store = {
    get(k, d) { try { const v = localStorage.getItem("cp." + k); return v == null ? d : JSON.parse(v); } catch { return d; } },
    set(k, v) { try { localStorage.setItem("cp." + k, JSON.stringify(v)); } catch { /* private mode */ } },
  };
  const S = {
    me: null,
    ws: null,
    book: "auto",
    provider: "all",
    days: store.get("days", 30),
    group: store.get("group", "service"),
    tableQuery: "",
    f: { status: "active", kind: "all", priority: "all", mine: false, q: "" },
    sort: { key: "amount", dir: "desc" },
    currency: "USD",
    last: null,
  };

  const PROVIDER_COLOR = { azure: "var(--s1)", aws: "var(--s2)", oci: "var(--s3)", gcp: "var(--s4)" };
  const PROVIDER_NAME = { azure: "Azure", aws: "AWS", oci: "Oracle Cloud", gcp: "Google Cloud" };
  const SERIES = ["var(--s1)", "var(--s2)", "var(--s3)", "var(--s4)", "var(--s5)"];
  const AVATAR = ["#355c8c", "#8a4f24", "#2f6b55", "#6b3f73", "#8a3b3b", "#4d5d2a"];
  const SOURCE_TEXT = { cloudtrail: "AWS CloudTrail", activity_log: "Azure Activity Log", example: "Example record" };

  // ================================================================ format
  const money = (n, digits = 2) => {
    try {
      return new Intl.NumberFormat("en-IN", { style: "currency", currency: S.currency, minimumFractionDigits: digits, maximumFractionDigits: digits }).format(n || 0);
    } catch { return "$" + Number(n || 0).toFixed(digits); }
  };
  const moneyAxis = (n) => {
    if (n >= 1000) {
      const k = n / 1000;
      const digits = Number.isInteger(k) ? 0 : Number.isInteger(k * 10) ? 1 : 2;
      return money(k, digits) + "k";
    }
    return money(n, n > 0 && n < 10 ? 2 : 0);
  };
  const pct = (x, signed = false) => {
    const v = x * 100;
    const s = Math.abs(v) < 10 ? v.toFixed(1) : Math.round(v).toString();
    return (signed && v > 0 ? "+" : "") + s + "%";
  };
  const D = (iso) => new Date(iso.length === 10 ? iso + "T00:00:00" : iso);
  const fDay = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short" });
  const fDayY = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" });
  const fWeek = new Intl.DateTimeFormat("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
  const dayShort = (iso) => fDay.format(D(iso));
  const dayLong = (iso) => fDayY.format(D(iso));
  function ago(iso) {
    if (!iso) return "never";
    const s = Math.round((Date.now() - D(iso).getTime()) / 1000);
    if (s < 45) return "just now";
    const m = Math.round(s / 60);
    if (m < 60) return m <= 1 ? "a minute ago" : `${m} minutes ago`;
    const h = Math.round(m / 60);
    if (h < 24) return h === 1 ? "an hour ago" : `${h} hours ago`;
    return dayLong(iso);
  }
  const initials = (name) => {
    if (!name) return "?";
    const base = name.split("@")[0].split("/").pop();
    const parts = base.split(/[._\-\s]+/).filter(Boolean);
    return ((parts[0] || "?")[0] + (parts[1] ? parts[1][0] : (parts[0] || "")[1] || "")).toUpperCase();
  };
  const avatarColor = (name) => AVATAR[[...(name || "")].reduce((a, c) => a + c.charCodeAt(0), 0) % AVATAR.length];
  const avatar = (name) => name
    ? `<span class="avatar" style="background:${avatarColor(name)}" aria-hidden="true">${esc(initials(name))}</span>`
    : `<span class="avatar none" aria-hidden="true">?</span>`;
  const who = (name) => name ? `<span class="who" title="${esc(name)}">${esc(name)}</span>` : `<span class="who none">No record</span>`;
  const delta = (change, goodWhenDown = true) => {
    if (change == null) return "";
    const cls = Math.abs(change) < 0.005 ? "flat" : (change > 0) === goodWhenDown ? "up" : "down";
    const arrow = change > 0 ? "▲" : change < 0 ? "▼" : "";
    return `<span class="delta ${cls}">${arrow} ${pct(Math.abs(change))}</span>`;
  };

  // ================================================================ api
  async function api(path, opts = {}) {
    const init = { credentials: "same-origin", ...opts, headers: { ...(opts.headers || {}) } };
    if (init.method && init.method !== "GET") init.headers["X-CloudPulse"] = "1";
    const res = await fetch(path, init);
    if (res.status === 401) { location.replace("/login"); throw new Error("Signed out"); }
    let body = null;
    try { body = await res.json(); } catch { /* empty */ }
    if (!res.ok) throw new Error((body && body.detail) || `Server answered ${res.status}`);
    return body;
  }
  const postJSON = (path, data) => api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data || {}) });
  const wsq = (extra = {}) => new URLSearchParams({ ws: S.ws, ...extra }).toString();
  const q = (extra = {}) => wsq({ book: S.book, provider: S.provider, days: S.days, ...extra });
  const curWs = () => (S.me ? S.me.workspaces.find((w) => w.slug === S.ws) : null);
  const canEdit = () => !!(curWs() && curWs().can_edit);

  function toast(msg) {
    const t = $("#toast");
    t.textContent = msg;
    t.hidden = false;
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => { t.hidden = true; }, 2600);
  }
  async function copy(text) {
    try { await navigator.clipboard.writeText(text); toast("Copied to clipboard"); }
    catch { toast("Couldn't copy. Select the text and copy it by hand."); }
  }

  // ================================================================ labels
  const STATUS_TEXT = {
    open: "Open", assigned: "Assigned", in_progress: "In progress", resolved: "Fixed, checking",
    verified: "Verified", dismissed: "Dismissed", snoozed: "Snoozed",
  };
  const STAGE_TEXT = { open: "Open", assigned: "Owned", resolved: "Fixed, checking", verified: "Verified" };
  const STAGE_COLOR = { open: "var(--s-other)", assigned: "var(--s1)", resolved: "var(--s4)", verified: "var(--s3)" };
  const OWNER_SOURCE = {
    activity_log: "Azure Activity Log", cloudtrail: "AWS CloudTrail", tag: "owner tag",
    example: "example record", assigned: "assigned in CloudPulse", unknown: "no record",
  };
  const ACTION_TEXT = {
    assign: "Assign", start: "Start work", resolve: "Mark fixed", dismiss: "Dismiss",
    snooze: "Snooze", reopen: "Reopen", comment: "Comment",
  };
  const EVENT_ICON = { created: "+", assigned: "→", status: "•", comment: "“", verified: "✓", reopened: "↺", regressed: "↺", updated: "Δ" };
  const prio = (f) => `<span class="prio ${esc(f.priority)}" title="Priority score ${f.priority_score} of 100">${esc(f.priority)}</span>`;
  const statusTag = (s) => `<span class="status ${esc(s)}">${esc(STATUS_TEXT[s] || s)}</span>`;
  const person = (p, fallback = "Unassigned") => {
    const label = p ? (typeof p === "string" ? p : (p.name || p.email)) : null;
    const key = p ? (typeof p === "string" ? p : p.email) : null;
    return label
      ? `<span class="person" title="${esc(key)}">${avatar(key)}<span>${esc(label)}</span></span>`
      : `<span class="person none">${esc(fallback)}</span>`;
  };
  const moneyMonth = (n) => `${money(n)}<small>a month</small>`;

  // ================================================================ shell
  const PAGES = {
    overview: { title: "Overview", sub: "Spend, what needs fixing, and what fixing has actually saved.", controls: "full", render: renderOverview },
    costs: { title: "Cost explorer", sub: "Break spend down by service or provider and compare with the period before.", controls: "full", render: renderCosts },
    anomalies: { title: "Anomalies", sub: "Days that cost far more than the same weekday usually does, and what drove them.", controls: "none", render: renderAnomalies },
    budgets: { title: "Budgets", sub: "This month against a limit, with a forecast and its uncertainty.", controls: "book", render: renderBudgets },
    findings: { title: "Findings", sub: "Every cost problem as a ranked, owned task that is checked against the bill once fixed.", controls: "none", render: renderFindings },
    owners: { title: "Owners", sub: "Who each finding belongs to, from audit logs first and tags second.", controls: "none", render: renderOwners },
    savings: { title: "Savings", sub: "Savings counted only after the bill shows the drop.", controls: "none", render: renderSavings },
    sources: { title: "Data sources", sub: "Connected accounts and imported bills. Access is read-only.", controls: "none", render: renderSources },
    admin: { title: "Workspaces & users", sub: "Create customer workspaces, connect their clouds and manage who can sign in.", controls: "none", render: renderAdmin, admin: true },
    audit: { title: "Audit log", sub: "Every sign-in, change and action, newest first.", controls: "none", render: renderAudit, admin: true },
  };
  const ALIASES = { waste: "findings" };
  const current = () => {
    const name = location.hash.replace(/^#\/?/, "").split("?")[0] || "overview";
    return ALIASES[name] || name;
  };
  const hashParams = () => new URLSearchParams(location.hash.split("?")[1] || "");

  function setControls(mode, meta) {
    const show = mode !== "none";
    $("#book-switch").hidden = !show;
    $("#provider-select").parentElement.hidden = !show;
    $("#range-switch").hidden = mode !== "full";
    if (!show || !meta) return;

    const book = $("#book-switch");
    if (meta.books.length > 1) {
      book.innerHTML = meta.books.map((b) =>
        `<button type="button" role="radio" data-book="${b}" aria-checked="${b === meta.book}">${b === "live" ? "Connected" : "Imported bill"}</button>`).join("");
    } else book.innerHTML = "";

    const sel = $("#provider-select");
    const opts = [{ id: "all", label: "All providers" }, ...meta.providers];
    sel.innerHTML = opts.map((p) => `<option value="${p.id}" ${p.id === meta.provider ? "selected" : ""}>${esc(p.label)}</option>`).join("");
    sel.disabled = meta.providers.length < 2 && meta.provider === "all";

    $$("#range-switch button").forEach((b) => b.setAttribute("aria-checked", String(Number(b.dataset.days) === S.days)));
  }

  function setBanner(meta, conn) {
    const el = $("#banner");
    const w = curWs();
    const connected = !!(conn && conn.connected && conn.connected.length);
    let html = "";
    if (PAGES[current()] && PAGES[current()].admin) {
      html = "";
    } else if (w && w.kind === "demo") {
      html = `<span><b>You're in the demo.</b> Spend is the FinOps Foundation's FOCUS sample bill (real, anonymised company data). The findings are examples, but their scores, forecasts and savings checks are calculated by the same code that runs on a live account. Nothing here can be changed.</span>`;
    } else if (meta && meta.book === "focus") {
      html = `<span>Spend shown is from the imported file <b>${esc(meta.dataset || "FOCUS export")}</b>.${connected ? " Resource findings and owners come from the connected account." : ""}</span>`;
    } else if (conn && !(conn.items || []).length) {
      html = S.me.is_admin
        ? `<span><b>No cloud account is connected to this workspace.</b> <a href="#/admin">Connect one under Workspaces &amp; users</a>.</span>`
        : `<span><b>No cloud account is connected to this workspace yet.</b> Ask your CloudPulse administrator to connect one.</span>`;
    } else if (conn && !connected && conn.last_run) {
      html = `<span><b>The last sync couldn't reach your cloud account.</b> <a href="#/sources">See what went wrong</a>.</span>`;
    } else if (conn && !conn.last_run) {
      html = conn.running ? "" : `<span><b>Not synced yet.</b> The first sync starts a few seconds after the server does.</span>`;
    } else if (meta && meta.total === 0 && connected) {
      html = `<span><b>Connected.</b> No spend recorded yet: Azure can take 8–24 hours to publish cost data for new usage. Resource findings and owners are already live.</span>`;
    }
    el.innerHTML = html;
    el.hidden = !html;
    if (conn && conn.running) watchSync();
  }

  function setFoot(conn) {
    if (!conn) return;
    const pill = $("#source-pill");
    const w = curWs();
    const names = [...new Set((conn.connected || []).map((k) => PROVIDER_NAME[k] || k))];
    if (w && w.kind === "demo") { pill.className = "source-pill sample"; pill.lastElementChild.textContent = "Demo data"; }
    else if (names.length) { pill.className = "source-pill live"; pill.lastElementChild.textContent = `Live: ${names.join(", ")}`; }
    else { pill.className = "source-pill"; pill.lastElementChild.textContent = "Not connected"; }
    $("#last-read").textContent = conn.last_run ? `Synced ${ago(conn.last_run)}` : "Not synced yet";
  }

  function setCounts(active, anomalies) {
    const f = $("#nav-findings"), a = $("#nav-anomalies");
    if (active != null) { f.textContent = active; f.hidden = !active; }
    if (anomalies != null) { a.textContent = anomalies; a.hidden = !anomalies; }
  }
  async function loadCounts() {
    if (!S.ws) return;
    try {
      const r = await api(`/api/findings?${wsq({ status: "active" })}`);
      const an = (r.kinds || []).find((k) => k.id === "anomaly");
      setCounts(r.counts.active, an ? an.count : 0);
    } catch { /* counts are a nicety */ }
  }

  function applyPlain(data) {
    setControls("none");
    setBanner(null, data && data.connections);
    if (data && data.connections) setFoot(data.connections);
  }

  async function route() {
    if (!S.me) return;
    let name = PAGES[current()] ? current() : "overview";
    if (PAGES[name].admin && !S.me.is_admin) name = "overview";
    const page = PAGES[name];
    $("#refresh").hidden = !canEdit() || !!page.admin;
    $("#readonly-pill").hidden = canEdit() || !!page.admin;
    $$(".nav a").forEach((a) => { if (a.dataset.page !== name) a.removeAttribute("aria-current"); else a.setAttribute("aria-current", "page"); });
    $("#page-title").textContent = page.title;
    $("#page-sub").textContent = page.sub;
    document.title = `${page.title} · CloudPulse`;
    closeNav();
    tip.hide();
    const root = $("#page");
    root.onclick = null;
    if (!route.soft) root.innerHTML = skeleton();
    setControls(page.controls, null);
    redraw = null;
    try {
      await page.render(root, page);
    } catch (err) {
      root.innerHTML = `<div class="card empty"><h3>Couldn't load this page</h3><p>${esc(err.message)}</p></div>`;
    }
    const open = hashParams().get("finding");
    if (open && $("#drawer").hidden) openFinding(Number(open));
  }
  // Re-render the current page in place (after an action), without the skeleton flash.
  async function refreshPage() {
    const y = window.scrollY;
    route.soft = true;
    try { await route(); } finally { route.soft = false; }
    window.scrollTo(0, y);
    loadCounts();
  }
  const skeleton = () => `
    <div class="grid g-4">${'<div class="card kpi"><div class="skeleton" style="height:14px;width:50%"></div><div class="skeleton" style="height:28px;width:70%"></div></div>'.repeat(4)}</div>
    <div class="card" style="height:320px;padding:18px"><div class="skeleton" style="height:100%"></div></div>`;

  function applyMeta(meta, page) {
    S.currency = meta.currency || S.currency;
    if (meta.book) S.book = meta.book;
    setControls(page.controls, meta);
    setBanner(meta, meta.connections);
    if (meta.connections) setFoot(meta.connections);
  }

  // ================================================================ sync progress
  let syncTimer = null;
  function watchSync(runId) {
    if (syncTimer) return;
    const strip = $("#sync-strip");
    const ws = S.ws;
    strip.hidden = false;
    $("#sync-step").textContent = "Starting";
    const tick = async () => {
      if (S.ws !== ws) { stop(); return; }
      let r;
      try { r = await api(`/api/sync?${wsq(runId ? { run_id: runId } : {})}`); } catch { stop(); return; }
      if (r.status === "queued" || r.status === "running") {
        $("#sync-step").textContent = r.step || "Working";
        syncTimer = setTimeout(tick, 1500);
        return;
      }
      stop();
      const entries = Object.values(r.detail || {});
      const bad = entries.filter((v) => v.state === "error").length;
      if (r.status === "failed") toast(`Sync failed${r.detail && r.detail.error ? `: ${r.detail.error}` : ""}`);
      else if (r.status) toast(bad ? `Sync finished · ${bad} connection failed` : "Sync finished");
      refreshPage();
    };
    const stop = () => { clearTimeout(syncTimer); syncTimer = null; strip.hidden = true; const b = $("#refresh"); b.disabled = false; b.classList.remove("spinning"); };
    syncTimer = setTimeout(tick, 400);
  }

  // ================================================================ notifications
  async function loadNotifications(openPanel = false) {
    let n;
    try { n = await api("/api/notifications"); } catch { return; }
    const dot = $("#bell-dot");
    dot.textContent = n.unread > 9 ? "9+" : n.unread;
    dot.hidden = !n.unread;
    if (!openPanel && $("#notif-panel").hidden) return;
    $("#notif-read-all").hidden = !n.unread;
    $("#notif-list").innerHTML = n.items.length ? n.items.map((x) => `
      <button class="notif ${x.read ? "" : "unread"}" type="button" data-id="${x.id}" data-finding="${x.finding_id || ""}" data-ws="${esc(x.workspace || "")}">
        <i aria-hidden="true"></i>
        <span><p>${esc(x.message)}</p><small>${ago(x.at)}${S.me.workspaces.length > 1 && x.workspace_name ? ` · ${esc(x.workspace_name)}` : ""}</small></span>
      </button>`).join("")
      : `<div class="empty"><h3>Nothing new</h3><p>You'll hear here when a finding is assigned to you, fixed, verified or comes back.</p></div>`;
  }
  function toggleNotifications(force) {
    const p = $("#notif-panel");
    const show = force != null ? force : p.hidden;
    p.hidden = !show;
    $("#bell").setAttribute("aria-expanded", String(show));
    if (show) loadNotifications(true);
  }
  $("#bell").onclick = (e) => { e.stopPropagation(); toggleNotifications(); };
  $("#notif-panel").onclick = async (e) => {
    e.stopPropagation();
    const b = e.target.closest(".notif");
    if (!b) return;
    await postJSON("/api/notifications/read", { ids: [Number(b.dataset.id)] }).catch(() => {});
    toggleNotifications(false);
    loadNotifications();
    if (b.dataset.ws && b.dataset.ws !== S.ws && S.me.workspaces.some((w) => w.slug === b.dataset.ws)) {
      selectWorkspace(b.dataset.ws); renderUser(); await route();
    }
    if (b.dataset.finding) openFinding(Number(b.dataset.finding));
  };
  $("#notif-read-all").onclick = async (e) => {
    e.stopPropagation();
    await postJSON("/api/notifications/read", {});
    loadNotifications(true);
  };
  document.addEventListener("click", () => { if (!$("#notif-panel").hidden) toggleNotifications(false); });

  // ================================================================ overview
  async function renderOverview(root, page) {
    const [o, m] = await Promise.all([api(`/api/overview?${q()}`), api(`/api/month?${q()}`)]);
    S.last = o;
    applyMeta(o, page);
    const P = o.pipeline;
    const L = o.savings;
    const stages = Object.fromEntries(P.stages.map((s) => [s.stage, s]));
    const openCount = (stages.open ? stages.open.count : 0) + (stages.assigned ? stages.assigned.count : 0);
    const openMonthly = (stages.open ? stages.open.monthly : 0) + (stages.assigned ? stages.assigned.monthly : 0);
    setCounts(null, P.anomalies_open);
    loadCounts();

    const provGroups = o.by_provider.groups.map((g) => ({
      key: g.key, label: PROVIDER_NAME[g.key] || g.key, color: PROVIDER_COLOR[g.key] || "var(--s-other)", total: g.total,
    }));
    const anomalySet = new Set(o.anomaly_dates);
    const changeText = o.change == null ? "" :
      Math.abs(o.change) < 0.005 ? ", the same as the period before" :
      `, <b>${pct(Math.abs(o.change))} ${o.change > 0 ? "more" : "less"}</b> than the ${o.window.days} days before`;
    const f = o.forecast;
    const done = !f.days_remaining;
    const maxStage = Math.max(1, ...P.stages.map((s) => s.monthly));

    root.innerHTML = `
      <section class="card summary-card">
        <p class="summary">
          ${o.total > 0 ? `You spent <b>${money(o.total)}</b> between ${dayShort(o.window.start)} and ${dayShort(o.window.end)}${changeText}.` : `Nothing billed between ${dayShort(o.window.start)} and ${dayShort(o.window.end)}.`}
          ${openCount ? `<b>${openCount} finding${openCount > 1 ? "s" : ""}</b> worth <b>${money(openMonthly)} a month</b> ${openCount > 1 ? "are" : "is"} waiting to be fixed` : "Nothing is waiting to be fixed"}${L.verified_count ? `, and fixes have already cut <b>${money(L.verified_monthly)} a month</b> off the bill.` : "."}
        </p>
        <a class="btn" href="#/findings">Open findings <svg><use href="#i-arrow"/></svg></a>
      </section>

      <section class="grid g-4" aria-label="Key figures">
        <div class="card kpi">
          <div class="kpi-label">Spend, last ${o.window.days} days</div>
          <div class="kpi-value num">${money(o.total)}</div>
          <div class="kpi-sub">${o.change != null ? `${delta(o.change)} vs ${money(o.previous_total, 0)} before` : "No earlier period to compare"}</div>
        </div>
        <div class="card kpi">
          <div class="kpi-label">${done ? "Total" : "Forecast"} for ${esc(f.month_label)}</div>
          <div class="kpi-value num">${money(f.forecast)}</div>
          ${f.budget ? `
            <div class="progress" title="Budget used"><i class="${f.forecast_ratio > 1 ? "over" : ""}" style="width:${Math.min(100, f.used * 100)}%"></i><b style="left:${Math.min(99, (f.forecast_ratio || 0) * 100)}%"></b></div>
            <div class="kpi-sub">${pct(f.forecast_ratio)} of ${money(f.budget, 0)}${f.breach_date ? ` · <span style="color:var(--bad)">over on ${dayShort(f.breach_date)}</span>` : ""}</div>`
          : `<div class="kpi-sub">${done ? "Month complete" : `range ${money(f.low, 0)}–${money(f.high, 0)}`} · <a class="linkbtn" href="#/budgets">Set a budget</a></div>`}
        </div>
        <div class="card kpi">
          <div class="kpi-label">Waiting to be fixed</div>
          <div class="kpi-value num">${money(openMonthly)}</div>
          <div class="kpi-sub">a month · ${openCount} finding${openCount === 1 ? "" : "s"}${P.governance_open ? ` · ${P.governance_open} governance` : ""}</div>
        </div>
        <div class="card kpi">
          <div class="kpi-label">Verified savings</div>
          <div class="kpi-value num" style="${L.verified_monthly ? "color:var(--good)" : ""}">${money(L.verified_monthly)}</div>
          <div class="kpi-sub">${L.verified_count ? `a month · ${money(L.saved_to_date)} saved so far${L.accuracy != null ? ` · estimates ${pct(L.accuracy)} accurate` : ""}` : "Counted once the bill shows the drop"}</div>
        </div>
      </section>

      <section class="card">
        <div class="card-head">
          <div><h2>From finding to verified saving</h2><p>Resource findings by stage, with what they're worth each month. Anomalies, budgets and tagging are tracked but not counted as savings.</p></div>
          <a class="linkbtn" href="#/savings">Savings ledger <svg><use href="#i-arrow"/></svg></a>
        </div>
        <div class="loop" style="margin-top:12px;border-top:1px solid var(--line)">
          ${["open", "assigned", "resolved", "verified"].map((k) => {
            const s = stages[k] || { count: 0, monthly: 0 };
            const tab = k === "verified" ? "verified" : k === "resolved" ? "resolved" : "active";
            return `<a class="loop-stage" href="#/findings" data-tab="${tab}">
              <small><i class="swatch" style="background:${STAGE_COLOR[k]}"></i>${STAGE_TEXT[k]}</small>
              <span class="v">${s.count}</span>
              <span class="m">${money(s.monthly)} a month</span>
              <span class="bar"><i style="width:${(s.monthly / maxStage) * 100}%;background:${STAGE_COLOR[k]}"></i></span>
            </a>`;
          }).join("")}
        </div>
        <div class="card-foot"><div class="loop-foot">
          <span><b>${P.dismissed}</b> dismissed with a reason</span>
          <span><b>${P.snoozed}</b> snoozed</span>
          <span><b>${P.anomalies_open}</b> anomal${P.anomalies_open === 1 ? "y" : "ies"} being tracked</span>
          <span><b>${P.governance_open}</b> governance finding${P.governance_open === 1 ? "" : "s"}</span>
        </div></div>
      </section>

      <section class="grid g-main">
        <div class="card">
          <div class="card-head">
            <div><h2>Daily spend</h2><p>Split by provider. Ringed days were flagged as anomalies.</p></div>
            <button class="linkbtn" id="trend-table-toggle" type="button">Table</button>
          </div>
          <div class="card-body">
            <div class="legend">
              ${provGroups.map((g) => `<span><i class="swatch" style="background:${g.color}"></i>${esc(g.label)} <b>${money(g.total, 0)}</b></span>`).join("")}
              <span><i class="dash"></i>Typical day ${moneyAxis(o.daily_average)}</span>
              ${anomalySet.size ? `<span><i class="ring"></i>Anomaly</span>` : ""}
            </div>
            <div id="trend"></div>
            <div id="trend-table" class="table-wrap" hidden style="max-height:260px;margin-top:12px"></div>
          </div>
        </div>

        <div class="card">
          <div class="card-head"><div><h2>Fix these first</h2><p>Ranked by priority score</p></div></div>
          <div class="card-body">
            <div class="feed">
              ${o.top_findings.length ? o.top_findings.map((x) => `
                <a class="feed-row" href="#/findings" data-finding="${x.id}" style="grid-template-columns:auto minmax(0,1fr) auto;column-gap:10px">
                  <span style="grid-row:1 / span 2;align-self:center">${prio(x)}</span>
                  <span class="feed-title" style="grid-column:2">${esc(x.title)}</span>
                  <span class="feed-val" style="grid-column:3">${money(x.monthly_impact)}<small>${x.governance || x.kind === "anomaly" ? "at stake" : "a month"}</small></span>
                  <span class="feed-meta" style="grid-column:2">${esc(x.kind_label)} · ${x.assignee ? esc(x.assignee.name || x.assignee.email) : x.owner ? esc(x.owner) : "no owner yet"}</span>
                </a>`).join("") : `<p class="muted">Nothing open. Well done.</p>`}
            </div>
          </div>
          <div class="card-foot"><span class="muted small">${openCount + P.governance_open} open in total</span><a class="linkbtn" href="#/findings">All findings <svg><use href="#i-arrow"/></svg></a></div>
        </div>
      </section>

      <section class="grid g-3">
        <div class="card">
          <div class="card-head"><div><h2>${esc(m.forecast.month_label)}</h2><p>${m.forecast.days_remaining ? `Forecast with an 80% range` : "Month complete"}</p></div><a class="linkbtn" href="#/budgets">Budget <svg><use href="#i-arrow"/></svg></a></div>
          <div class="card-body"><div id="month-mini"></div></div>
          <div class="card-foot"><span class="muted small">${money(m.forecast.month_to_date)} spent${m.budget ? ` of ${money(m.budget, 0)}` : ""}</span><span class="small">${m.forecast.days_remaining ? `${m.forecast.days_remaining} days left · forecast ${money(m.forecast.forecast)}` : `total ${money(m.forecast.forecast)}`}</span></div>
        </div>

        <div class="card">
          <div class="card-head"><div><h2>Top services</h2><p>${o.service_count} services billed in this period</p></div></div>
          <div class="card-body">
            <div class="bar-list">
              ${o.services.length ? o.services.slice(0, 5).map((s) => `
                <div class="item">
                  <span class="name" title="${esc(s.service)}">${esc(s.service)}${o.providers.length > 1 ? `<small>${esc(s.provider_label)}</small>` : ""}</span>
                  <span class="val">${money(s.amount)}</span>
                  <span class="track"><i style="width:${(s.amount / o.services[0].amount) * 100}%;background:${PROVIDER_COLOR[s.provider] || "var(--s1)"}"></i></span>
                </div>`).join("") : `<p class="muted">No services billed.</p>`}
            </div>
          </div>
          <div class="card-foot"><span class="muted small">${o.untagged ? `${pct(o.untagged.share)} of spend has no tags` : "Bars coloured by provider"}</span><a class="linkbtn" href="#/costs">Explorer <svg><use href="#i-arrow"/></svg></a></div>
        </div>

        <div class="card">
          <div class="card-head"><div><h2>Owners</h2><p>Open and verified, per person</p></div></div>
          <div class="card-body">
            <div class="feed">
              ${o.owners.length ? o.owners.slice(0, 5).map((p) => `
                <a class="feed-row" href="#/owners" style="grid-template-columns:auto minmax(0,1fr) auto;column-gap:10px">
                  <span style="grid-row:1 / span 2">${avatar(p.owner)}</span>
                  <span class="feed-title" style="grid-column:2">${p.owner ? esc(p.owner) : "No owner found"}</span>
                  <span class="feed-val" style="grid-column:3">${money(p.open_monthly)}<small>${p.verified_monthly ? `${money(p.verified_monthly)} saved` : "open"}</small></span>
                  <span class="feed-meta" style="grid-column:2">${p.open} open · ${p.verified} verified</span>
                </a>`).join("") : `<p class="muted">No owners to show.</p>`}
            </div>
          </div>
          <div class="card-foot"><span class="muted small">Audit log first, tags second</span><a class="linkbtn" href="#/owners">All owners <svg><use href="#i-arrow"/></svg></a></div>
        </div>
      </section>`;

    const draw = () => {
      bars($("#trend"), {
        days: o.by_provider.days, groups: provGroups, anomalies: anomalySet,
        ref: { value: o.daily_average }, fmt: money, fmtAxis: moneyAxis, fmtDate: dayShort, fmtDateLong: dayLong,
        label: `Daily spend by provider, ${o.window.days} days`,
      });
      cumulative($("#month-mini"), {
        path: m.forecast.path, budget: m.budget, low: m.forecast.low, high: m.forecast.high,
        breach: m.forecast.breach_date, height: 190,
        fmt: money, fmtAxis: moneyAxis, fmtDate: dayShort, fmtDateLong: dayLong,
      });
    };
    draw();
    redraw = draw;

    $("#trend-table").innerHTML = `<table class="data"><thead><tr><th>Day</th>${provGroups.map((g) => `<th class="r">${esc(g.label)}</th>`).join("")}<th class="r">Total</th></tr></thead><tbody>${
      o.by_provider.days.map((d) => {
        const t = provGroups.reduce((s, g) => s + (d.values[g.key] || 0), 0);
        return `<tr><td>${dayLong(d.date)}${anomalySet.has(d.date) ? ' <span class="badge bad">Anomaly</span>' : ""}</td>${provGroups.map((g) => `<td class="r">${money(d.values[g.key] || 0)}</td>`).join("")}<td class="r"><b>${money(t)}</b></td></tr>`;
      }).join("")}</tbody></table>`;
    $("#trend-table-toggle").onclick = (e) => {
      const t = $("#trend-table");
      t.hidden = !t.hidden;
      e.target.textContent = t.hidden ? "Table" : "Hide table";
    };
    root.onclick = (e) => {
      const a = e.target.closest("[data-finding]");
      if (a) { e.preventDefault(); openFinding(Number(a.dataset.finding)); return; }
      const st = e.target.closest("[data-tab]");
      if (st) S.f.status = st.dataset.tab;
    };
  }

  // ================================================================ cost explorer
  async function renderCosts(root, page) {
    const e = await api(`/api/explorer?${q({ group: S.group })}`);
    applyMeta(e, page);
    const groups = e.stack.groups.map((g, i) => ({
      key: g.key, total: g.total,
      label: g.key,
      color: g.key === "Other" ? "var(--s-other)" : S.group === "provider"
        ? (PROVIDER_COLOR[Object.keys(PROVIDER_NAME).find((k) => PROVIDER_NAME[k] === g.key)] || SERIES[i])
        : SERIES[i],
    }));
    const noun = S.group === "service" ? "service" : "provider";

    root.innerHTML = `
      <section class="grid g-4">
        <div class="card kpi"><div class="kpi-label">Total</div><div class="kpi-value num">${money(e.total)}</div><div class="kpi-sub">${dayShort(e.window.start)} – ${dayLong(e.window.end)}</div></div>
        <div class="card kpi"><div class="kpi-label">Previous ${e.window.days} days</div><div class="kpi-value num">${e.previous_total ? money(e.previous_total) : "—"}</div><div class="kpi-sub">${e.previous_total ? delta((e.total - e.previous_total) / e.previous_total) + " change" : "No billing data for that period"}</div></div>
        <div class="card kpi"><div class="kpi-label">${noun === "service" ? "Services" : "Providers"} billed</div><div class="kpi-value num">${e.table.length}</div><div class="kpi-sub">${e.table[0] ? `Largest: ${esc(e.table[0].key)}` : ""}</div></div>
        <div class="card kpi"><div class="kpi-label">Daily average</div><div class="kpi-value num">${money(e.total / e.window.days)}</div><div class="kpi-sub">Across all ${e.window.days} days</div></div>
      </section>

      <section class="card">
        <div class="card-head">
          <div><h2>Spend by ${noun}</h2><p>Top five, with everything else grouped as Other.</p></div>
          <div class="seg" role="radiogroup" aria-label="Group by" id="group-switch">
            <button type="button" role="radio" data-group="service" aria-checked="${S.group === "service"}">Service</button>
            <button type="button" role="radio" data-group="provider" aria-checked="${S.group === "provider"}">Provider</button>
          </div>
        </div>
        <div class="card-body">
          <div class="legend">${groups.map((g) => `<span><i class="swatch" style="background:${g.color}"></i>${esc(g.label)} <b>${money(g.total, 0)}</b></span>`).join("")}</div>
          <div id="stack"></div>
        </div>
      </section>

      <section class="card">
        <div class="table-tools">
          <label class="search"><svg><use href="#i-search"/></svg><span class="sr-only">Search</span><input id="table-search" type="search" placeholder="Search ${noun}s" value="${esc(S.tableQuery)}"></label>
          <span class="muted small" id="table-count"></span>
          <button class="btn btn-sm" id="csv" type="button" style="margin-left:auto"><svg><use href="#i-download"/></svg>CSV</button>
        </div>
        <div class="table-wrap">
          <table class="data" id="cost-table">
            <thead><tr>
              <th data-key="key" scope="col"><button type="button">${noun === "service" ? "Service" : "Provider"}</button></th>
              ${noun === "service" ? '<th class="hide-sm" scope="col">Provider</th>' : ""}
              <th class="r" data-key="amount" scope="col"><button type="button">Spend</button></th>
              <th class="r hide-sm" data-key="share" scope="col"><button type="button">Share</button></th>
              <th class="r hide-sm" data-key="previous" scope="col"><button type="button">Before</button></th>
              <th class="r" data-key="change" scope="col"><button type="button">Change</button></th>
            </tr></thead>
            <tbody></tbody>
          </table>
        </div>
        <div class="card-foot" style="justify-content:center"><button class="linkbtn" type="button" id="more-rows" hidden></button></div>
      </section>`;
    S.showAll = false;

    const draw = () => bars($("#stack"), {
      days: e.stack.days, groups, fmt: money, fmtAxis: moneyAxis, fmtDate: dayShort, fmtDateLong: dayLong, height: 280,
      label: `Daily spend by ${noun}`,
    });
    draw();
    redraw = draw;

    const top = e.table[0] ? e.table[0].amount : 1;
    const fill = () => {
      const qy = S.tableQuery.toLowerCase();
      const rows = e.table.filter((r) => !qy || r.key.toLowerCase().includes(qy) || (r.provider_label || "").toLowerCase().includes(qy));
      const { key, dir } = S.sort;
      rows.sort((a, b) => {
        const av = a[key] ?? -Infinity, bv = b[key] ?? -Infinity;
        const c = typeof av === "string" ? av.localeCompare(bv) : av - bv;
        return dir === "asc" ? c : -c;
      });
      $$("#cost-table th[data-key]").forEach((th) => th.setAttribute("aria-sort", th.dataset.key === key ? (dir === "asc" ? "ascending" : "descending") : "none"));
      $("#table-count").textContent = `${rows.length} of ${e.table.length}`;
      const shown = S.showAll || qy ? rows : rows.slice(0, 15);
      $("#more-rows").hidden = shown.length === rows.length;
      $("#more-rows").textContent = `Show all ${rows.length} ${noun}s`;
      $("#cost-table tbody").innerHTML = rows.length ? shown.map((r) => `
        <tr>
          <td><span class="mini-track hide-sm"><i style="width:${(r.amount / top) * 100}%"></i></span><span class="cell-main">${esc(r.key)}</span></td>
          ${noun === "service" ? `<td class="hide-sm muted">${esc(r.provider_label)}</td>` : ""}
          <td class="r"><b style="font-weight:500">${money(r.amount)}</b></td>
          <td class="r hide-sm">${pct(r.share)}</td>
          <td class="r hide-sm muted">${r.previous ? money(r.previous) : "—"}</td>
          <td class="r">${r.change != null ? delta(r.change) : e.previous_total && !r.previous ? '<span class="badge">New</span>' : '<span class="muted">—</span>'}</td>
        </tr>`).join("") : `<tr><td colspan="6" class="empty">Nothing matches “${esc(S.tableQuery)}”.</td></tr>`;
      return rows;
    };
    fill();

    $("#group-switch").onclick = (ev) => {
      const b = ev.target.closest("button"); if (!b || b.dataset.group === S.group) return;
      S.group = b.dataset.group; store.set("group", S.group); S.tableQuery = ""; route();
    };
    $("#table-search").oninput = (ev) => { S.tableQuery = ev.target.value; fill(); };
    $("#more-rows").onclick = () => { S.showAll = true; fill(); };
    $$("#cost-table th[data-key] button").forEach((b) => b.onclick = () => {
      const key = b.parentElement.dataset.key;
      S.sort = { key, dir: S.sort.key === key && S.sort.dir === "desc" ? "asc" : "desc" };
      fill();
    });
    $("#csv").onclick = () => {
      const rows = fill();
      const lines = [[noun, "provider", "spend", "share", "previous", "change"].join(",")]
        .concat(rows.map((r) => [`"${r.key.replace(/"/g, '""')}"`, r.provider_label, r.amount, r.share, r.previous, r.change ?? ""].join(",")));
      const blob = new Blob([lines.join("\n")], { type: "text/csv" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `cloudpulse-${noun}s-${e.window.start}-to-${e.window.end}.csv`;
      a.click();
      URL.revokeObjectURL(a.href);
    };
  }

  // ================================================================ findings inbox
  const STATUS_TABS = [
    ["active", "To do"], ["resolved", "Fixed, checking"], ["verified", "Verified"], ["closed", "Dismissed & snoozed"], ["all", "All"],
  ];
  async function renderFindings(root) {
    S.f = S.f || { status: "active", kind: "all", priority: "all", mine: false, q: "" };
    const F = S.f;
    root.innerHTML = `
      <section class="grid g-4" id="f-kpis"></section>
      <section class="card">
        <div class="tabs" role="tablist" id="f-tabs"></div>
        <div class="table-tools">
          <label class="search"><svg><use href="#i-search"/></svg><span class="sr-only">Search</span><input id="f-search" type="search" placeholder="Search title, resource, owner" value="${esc(F.q)}"></label>
          <label><span class="sr-only">Kind</span><select class="filter-sel" id="f-kind"></select></label>
          <div class="chips" id="f-prio" role="group" aria-label="Priority"></div>
          <button class="chip" type="button" id="f-mine" aria-pressed="${F.mine}">Assigned to me</button>
          <button class="btn btn-sm" id="f-csv" type="button" style="margin-left:auto"><svg><use href="#i-download"/></svg>CSV</button>
        </div>
        <div class="table-wrap">
          <table class="data" id="f-table">
            <thead><tr>
              <th scope="col" data-key="priority_score" aria-sort="descending"><button type="button">Priority</button></th>
              <th scope="col">Finding</th>
              <th scope="col" class="hide-sm">Owner</th>
              <th scope="col" class="hide-sm">Status</th>
              <th scope="col" class="r" data-key="monthly_impact"><button type="button">Impact</button></th>
              <th scope="col" class="r hide-sm" data-key="age_days"><button type="button">Age</button></th>
            </tr></thead>
            <tbody id="f-body"></tbody>
          </table>
        </div>
      </section>
      <section class="card">
        <div class="card-head"><div><h2>How findings are ranked</h2><p>The same formula for every finding, so a $3 IP and a $300 VM can be compared fairly.</p></div></div>
        <div class="card-body">
          <div class="math">
            <div class="ln"><span>impact score</span><span>log₁₀(1 + monthly $) ÷ log₁₀(1001)  →  $1 ≈ 0.10, $100 ≈ 0.67, $1,000 = 1</span></div>
            <div class="ln"><span>severity weight</span><span>critical 1.0 · high 0.8 · medium 0.55 · low 0.3</span></div>
            <div class="ln"><span>age factor</span><span>1 + min(0.3, days open ÷ 100)</span></div>
            <div class="ln total"><span>score</span><span>100 × (0.6 × impact + 0.4 × severity) × confidence × age</span></div>
            <div class="ln"><span>bands</span><span>P1 ≥ 70 · P2 ≥ 45 · P3 ≥ 25 · P4 below</span></div>
          </div>
        </div>
      </section>`;

    let data = null;
    let sort = { key: "priority_score", dir: "desc" };
    const load = async () => {
      data = await api(`/api/findings?${wsq({ status: F.status, kind: F.kind, priority: F.priority, mine: F.mine, q: F.q })}`);
      applyPlain(data);
      paint();
    };
    const paint = () => {
      const c = data.counts;
      if (F.status === "active") {
        const an = (data.kinds || []).find((k) => k.id === "anomaly");
        setCounts(c.active, an ? an.count : null);
      }
      $("#f-tabs").innerHTML = STATUS_TABS.map(([k, label]) =>
        `<button type="button" role="tab" data-status="${k}" aria-selected="${F.status === k}">${label}<span class="n">${c[k] || 0}</span></button>`).join("");
      $("#f-kind").innerHTML = `<option value="all">All kinds</option>` + data.kinds.map((k) =>
        `<option value="${esc(k.id)}" ${F.kind === k.id ? "selected" : ""}>${esc(k.label)} (${k.count})</option>`).join("");
      $("#f-prio").innerHTML = ["all", "P1", "P2", "P3", "P4"].map((p) =>
        `<button class="chip" type="button" data-p="${p}" aria-pressed="${F.priority === p}">${p === "all" ? "Any priority" : p}${p !== "all" ? ` <span class="n">${data.priorities[p] || 0}</span>` : ""}</button>`).join("");
      $("#f-mine").innerHTML = `Assigned to me <span class="n">${data.mine_count}</span>`;
      $("#f-mine").setAttribute("aria-pressed", String(F.mine));

      const items = data.items.slice();
      const { key, dir } = sort;
      items.sort((a, b) => ((a[key] ?? 0) - (b[key] ?? 0)) * (dir === "asc" ? 1 : -1));
      $$("#f-table th[data-key]").forEach((th) => th.setAttribute("aria-sort", th.dataset.key === key ? (dir === "asc" ? "ascending" : "descending") : "none"));

      const savingsRows = items.filter((x) => !x.governance && x.kind !== "anomaly");
      const sum = savingsRows.reduce((s, x) => s + (F.status === "verified" ? (x.realized_monthly || 0) : x.monthly_impact), 0);
      const p1 = items.filter((x) => x.priority === "P1").length;
      const unowned = items.filter((x) => !x.assignee).length;
      const oldest = items.reduce((m, x) => Math.max(m, x.age_days || 0), 0);
      $("#f-kpis").innerHTML = `
        <div class="card kpi"><div class="kpi-label">Findings shown</div><div class="kpi-value num">${items.length}</div><div class="kpi-sub">${esc(STATUS_TABS.find((t) => t[0] === F.status)[1])}</div></div>
        <div class="card kpi"><div class="kpi-label">${F.status === "verified" ? "Verified saving" : "Savings at stake"}</div><div class="kpi-value num">${money(sum)}</div><div class="kpi-sub">a month, resource findings only</div></div>
        <div class="card kpi"><div class="kpi-label">P1</div><div class="kpi-value num" style="${p1 ? "color:var(--bad)" : ""}">${p1}</div><div class="kpi-sub">score 70 or more</div></div>
        <div class="card kpi"><div class="kpi-label">No one assigned</div><div class="kpi-value num">${unowned}</div><div class="kpi-sub">${items.length ? `oldest open ${Math.round(oldest)} days` : "—"}</div></div>`;

      $("#f-body").innerHTML = items.length ? items.map((x) => `
        <tr class="clickable" tabindex="0" data-id="${x.id}">
          <td><div class="prio-cell">${prio(x)}<span class="score">${x.priority_score}</span></div></td>
          <td>
            <div class="finding-title" title="${esc(x.title)}">${esc(x.title)}</div>
            <div class="finding-sub">${esc(x.kind_label)}${x.provider_label ? ` · ${esc(x.provider_label)}` : ""}${x.resource_group ? ` · ${esc(x.resource_group)}` : ""}${x.region ? ` · ${esc(x.region)}` : ""}</div>
          </td>
          <td class="hide-sm">${x.assignee ? person(x.assignee) : x.owner ? `<span title="Found in ${esc(OWNER_SOURCE[x.owner_source] || x.owner_source || "")}, not a CloudPulse user">${person(x.owner)}</span>` : person(null, x.governance || x.kind === "anomaly" ? "Workspace owners" : "Unassigned")}</td>
          <td class="hide-sm">${statusTag(x.status)}${x.status === "snoozed" && x.snoozed_until ? `<div class="cell-sub">until ${dayShort(x.snoozed_until)}</div>` : ""}</td>
          <td class="r money-cell">${x.status === "verified" && x.realized_monthly != null
            ? `<b style="color:var(--good)">${money(x.realized_monthly)}</b><small>verified · est. ${money(x.monthly_impact)}</small>`
            : `<b>${money(x.monthly_impact)}</b><small>${x.governance || x.kind === "anomaly" ? esc(x.impact_basis) : "a month"}</small>`}</td>
          <td class="r hide-sm muted">${Math.round(x.age_days || 0)}d</td>
        </tr>`).join("")
        : `<tr><td colspan="6"><div class="empty"><h3>${F.q || F.kind !== "all" || F.priority !== "all" || F.mine ? "Nothing matches" : F.status === "active" ? "Nothing to do" : "Nothing here yet"}</h3><p>${F.status === "active" ? "New findings appear after each sync." : "Try another tab or filter."}</p></div></td></tr>`;
    };

    await load();
    const open = (tr) => openFinding(Number(tr.dataset.id));
    $("#f-body").onclick = (e) => { const tr = e.target.closest("tr[data-id]"); if (tr) open(tr); };
    $("#f-body").onkeydown = (e) => { if (e.key === "Enter") { const tr = e.target.closest("tr[data-id]"); if (tr) open(tr); } };
    $("#f-tabs").onclick = (e) => { const b = e.target.closest("[data-status]"); if (b) { F.status = b.dataset.status; F.kind = "all"; F.priority = "all"; load(); } };
    $("#f-kind").onchange = (e) => { F.kind = e.target.value; F.priority = "all"; load(); };
    $("#f-prio").onclick = (e) => { const b = e.target.closest("[data-p]"); if (b) { F.priority = b.dataset.p; load(); } };
    $("#f-mine").onclick = () => { F.mine = !F.mine; load(); };
    let qt;
    $("#f-search").oninput = (e) => { clearTimeout(qt); qt = setTimeout(() => { F.q = e.target.value.trim(); load(); }, 250); };
    $$("#f-table th[data-key] button").forEach((b) => b.onclick = () => {
      const key = b.parentElement.dataset.key;
      sort = { key, dir: sort.key === key && sort.dir === "desc" ? "asc" : "desc" };
      paint();
    });
    $("#f-csv").onclick = () => {
      const cols = ["id", "priority", "priority_score", "kind_label", "title", "resource_name", "resource_group", "region", "status", "monthly_impact", "impact_basis", "realized_monthly", "confidence", "owner", "age_days"];
      const cell = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
      const lines = [cols.join(",")].concat(data.items.map((x) => cols.map((k) => cell(x[k])).concat(cell(x.assignee ? x.assignee.email : "")).join(",")));
      lines[0] += ",assignee";
      download(`cloudpulse-findings-${F.status}.csv`, lines.join("\n"), "text/csv");
    };
  }

  function download(name, text, type) {
    const blob = new Blob([text], { type });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }

  // ================================================================ finding drawer
  let lastFocus = null;
  let drawerId = null;
  function showDrawer(wide) {
    $("#drawer-panel").classList.toggle("wide", !!wide);
    if ($("#drawer").hidden) lastFocus = document.activeElement;
    $("#drawer").hidden = false;
  }
  function closeDrawer() {
    $("#drawer").hidden = true;
    $("#drawer-actions").innerHTML = "";
    drawerId = null;
    tip.hide();
    if (hashParams().get("finding")) history.replaceState(null, "", `#/${current()}`);
    if (lastFocus && lastFocus.isConnected) lastFocus.focus();
  }
  $("#drawer-close").onclick = closeDrawer;
  $("#drawer").onclick = (e) => { if (e.target.id === "drawer") closeDrawer(); };

  const kv = (pairs) => `<div class="evidence">${pairs.filter((p) => p && p[1] != null && p[1] !== "" && p[1] !== "—").map(([k, v]) => `<div><span>${esc(k)}</span><b>${v}</b></div>`).join("")}</div>`;
  const pctPlain = (v) => `${Number(v).toFixed(v < 10 ? 1 : 0)}%`;

  function evidenceHtml(d) {
    const e = d.evidence || {};
    if (d.kind === "anomaly") {
      const drivers = e.drivers || [];
      return `
        ${kv([["That day", money(e.amount)], ["Usual", money(e.expected)], ["Above usual", `+${money(e.excess)}`],
              ["Robust z-score", `${e.z} <small class="muted">(flag at 3.5)</small>`], ["Usual swing", money(e.spread)], ["Still high?", e.ongoing ? "Yes" : "No, one-off"]])}
        <div class="math" style="margin-top:10px">
          <div class="ln"><span>baseline</span><span>${esc(e.method || "")}</span></div>
          <div class="ln"><span>days used</span><span>${(e.baseline_days || []).map(dayShort).join(", ")}</span></div>
          <div class="ln"><span>z</span><span>(${money(e.amount)} − ${money(e.expected)}) ÷ ${money(e.spread)} = ${e.z}</span></div>
          <div class="ln total"><span>impact</span><span>${e.ongoing ? `${money(e.excess)} × 30.4 days = ${money(d.monthly_impact)} if it continues` : `${money(e.excess)} once`}</span></div>
        </div>
        ${drivers.length ? `<h3 style="margin-top:14px">What drove it</h3>
          <table class="data"><thead><tr><th>Service</th><th class="r">Usual</th><th class="r">That day</th><th class="r">Share</th></tr></thead><tbody>
          ${drivers.slice(0, 5).map((r) => `<tr><td class="clip" title="${esc(r.service)}">${esc(r.service)}</td><td class="r muted">${money(r.usual)}</td><td class="r">${money(r.amount)}</td><td class="r">${pct(r.share)}</td></tr>`).join("")}
          </tbody></table>` : ""}
        ${(e.resource_drivers || []).length ? `<h3 style="margin-top:14px">Resources behind it</h3>
          <table class="data"><tbody>${e.resource_drivers.map((r) => `<tr><td class="clip" title="${esc(r.resource_id)}">${esc(r.name)}</td><td class="r muted">usual ${money(r.usual)}</td><td class="r">+${money(r.increase)}</td></tr>`).join("")}</tbody></table>` : ""}`;
    }
    if (d.kind === "budget_risk") {
      const fc = e.forecast || {};
      return `
        ${kv([["Budget", money(e.budget)], [fc.days_remaining ? "Forecast" : "Spent", money(fc.forecast)], ["Over by", pct(e.overrun_ratio - 1)],
              ["Passes budget on", e.breach_date ? dayLong(e.breach_date) : "—"], ["80% range", fc.days_remaining ? `${money(fc.low, 0)}–${money(fc.high, 0)}` : "—"], ["Method", esc(fc.method || "")]])}
        ${(e.growth || []).length ? `<h3 style="margin-top:14px">What grew, vs the same days last month</h3>
          <table class="data"><thead><tr><th>Service</th><th class="r">Last month</th><th class="r">This month</th><th class="r">Change</th></tr></thead><tbody>
          ${e.growth.map((g) => `<tr><td class="clip" title="${esc(g.service)}">${esc(g.service)}</td><td class="r muted">${money(g.last_month_same_days)}</td><td class="r">${money(g.this_month)}</td><td class="r">${g.change > 0 ? "+" : ""}${money(g.change)}</td></tr>`).join("")}
          </tbody></table>` : ""}
        <p style="margin-top:10px"><a class="linkbtn" href="#/budgets" data-close>See the forecast chart <svg><use href="#i-arrow"/></svg></a></p>`;
    }
    if (d.kind === "idle_vm" || d.kind === "rightsize_vm") {
      const t1 = 5, t2 = 20, scale = Math.max(40, Math.ceil((e.cpu_peak || 0) / 10) * 10);
      const at = (v) => `${Math.min(100, (v / scale) * 100)}%`;
      const hourly = e.current_hourly != null && e.suggested_hourly != null;
      return `
        <p class="muted small">CPU over ${e.metrics_days || 14} days, hourly averages. Green = idle (&lt;${t1}%), amber = oversized (&lt;${t2}%).</p>
        <div class="gauge" style="--t1:${at(t1)};--t2:${at(t2)}">
          <div class="track"></div>
          <div class="mark" style="left:${at(e.cpu_p95)}" data-v="p95 ${pctPlain(e.cpu_p95)}"></div>
          <span class="tick" style="left:${at(t1)}">${t1}%</span><span class="tick" style="left:${at(t2)}">${t2}%</span><span class="tick" style="left:${at(e.cpu_peak)}">peak ${pctPlain(e.cpu_peak)}</span>
        </div>
        <div style="height:14px"></div>
        ${kv([["Size", esc(e.size)], ["Suggested", e.suggested_size ? esc(e.suggested_size) : (d.kind === "idle_vm" ? "Deallocate" : null)],
              ["CPU average", pctPlain(e.cpu_mean)], ["CPU p95", pctPlain(e.cpu_p95)], ["CPU peak", pctPlain(e.cpu_peak)],
              ["Network p95", `${e.net_p95_mb} MB/h`], ["Hours measured", `${e.hours}`], ["Coverage", pct(e.coverage || 0)]])}
        <div class="math" style="margin-top:10px">
          <div class="ln"><span>rule</span><span>${esc(e.rule)}</span></div>
          ${hourly ? `<div class="ln total"><span>saving</span><span>($${e.current_hourly} − $${e.suggested_hourly}) × 730 h = ${money(d.monthly_impact)}</span></div>` : ""}
        </div>
        ${e.note ? `<p class="callout" style="margin-top:10px">${esc(e.note)}</p>` : ""}
        ${e.advisor_agrees ? `<p class="callout" style="margin-top:10px"><b>Azure Advisor agrees.</b> ${esc(e.advisor_agrees.problem || "")}</p>` : ""}`;
    }
    if (d.kind === "untagged_spend") {
      return `
        ${kv([["Untagged share", pct(e.share)], ["Untagged, 30 days", money(e.untagged_30d)], ["All spend, 30 days", money(e.total_30d)],
              ["Owner found anyway", e.owner_coverage != null ? pct(e.owner_coverage) : "—"]])}
        ${(e.top_untagged || []).length ? `<h3 style="margin-top:14px">Largest untagged resources</h3>
          <table class="data"><tbody>${e.top_untagged.map((r) => `<tr><td class="clip" title="${esc(r.resource_id || r.name)}">${esc(r.name || r.resource_id)}</td><td>${r.owner ? person(r.owner) : '<span class="muted small">no owner found</span>'}</td><td class="r">${money(r.amount)}</td></tr>`).join("")}</tbody></table>` : ""}
        <p class="muted small" style="margin-top:8px">${esc(e.source || "")}</p>`;
    }
    const skip = new Set(["rule", "owner_trail", "extra_cost_ids", "details", "advisor_agrees"]);
    const pairs = Object.entries(e).filter(([k, v]) => !skip.has(k) && (typeof v !== "object" || v === null))
      .map(([k, v]) => [k.replace(/_/g, " "), esc(typeof v === "number" ? v.toLocaleString("en-IN") : v)]);
    return `${pairs.length ? kv(pairs) : ""}${e.rule ? `<div class="math" style="margin-top:10px"><div class="ln"><span>rule</span><span>${esc(e.rule)}</span></div></div>` : ""}
      ${e.details ? `<div class="math" style="margin-top:8px">${Object.entries(e.details).map(([k, v]) => `<div class="ln"><span>${esc(k)}</span><span>${esc(v)}</span></div>`).join("")}</div>` : ""}`;
  }

  function priorityHtml(d) {
    const b = d.priority_breakdown;
    if (!b) return "";
    const p = b.parts;
    const inner = 0.6 * p.impact_score + 0.4 * p.severity_weight;
    return `<div class="math">
      <div class="ln"><span>impact score</span><span>log₁₀(1 + ${p.weighted_impact.toFixed(2)}) ÷ 3 = ${p.impact_score.toFixed(3)}</span></div>
      <div class="ln"><span>severity (${esc(d.severity)})</span><span>${p.severity_weight}</span></div>
      <div class="ln"><span>blend</span><span>0.6 × ${p.impact_score.toFixed(3)} + 0.4 × ${p.severity_weight} = ${inner.toFixed(3)}</span></div>
      <div class="ln"><span>confidence</span><span>× ${p.confidence}</span></div>
      <div class="ln"><span>age factor</span><span>× ${p.age_factor}</span></div>
      <div class="ln total"><span>score</span><span>${b.score} → ${esc(b.band)}</span></div>
    </div>${p.weighted_impact !== d.monthly_impact ? `<p class="muted small" style="margin-top:6px">Governance findings count a quarter of their dollar figure, since the money isn't wasted, only unattributed.</p>` : ""}`;
  }

  function verificationHtml(d) {
    const v = d.verification;
    if (!v) {
      if (d.status === "resolved") return `<div class="verify-box waiting"><h4>Checking on the next sync</h4><p class="small">CloudPulse confirms the problem is gone, then compares 7 days of cost before and after the fix.</p></div>`;
      return "";
    }
    if (v.state === "verified") {
      const acc = d.monthly_impact ? (v.realized_monthly ?? d.realized_monthly) / d.monthly_impact : null;
      return `<div class="verify-box verified">
        <h4>Verified${d.verified_at ? ` on ${dayLong(d.verified_at)}` : ""}</h4>
        <div class="nums">
          ${v.before_daily != null ? `<div><b>${money(v.before_daily)}</b><span>a day before</span></div><div><b>${money(v.after_daily)}</b><span>a day after</span></div>` : ""}
          <div><b>${money(d.realized_monthly)}</b><span>saved a month</span></div>
          ${acc != null && !d.governance && d.kind !== "anomaly" ? `<div><b>${pct(acc)}</b><span>of the estimate</span></div>` : ""}
        </div>
        ${v.series_before ? `<div id="ba-chart"></div>` : ""}
        <p class="small">${esc(v.method || "")}${v.before_daily != null ? ` · (${money(v.before_daily)} − ${money(v.after_daily)}) × 30.4 = ${money(v.realized_monthly)}` : ""}${v.note ? ` · ${esc(v.note)}` : ""}</p>
      </div>`;
    }
    return `<div class="verify-box waiting">
      <h4>Not verified yet</h4>
      <p class="small">${esc(v.message || "Waiting for more cost data.")}</p>
      ${v.limit != null ? `<p class="small">Needs the last 3 billed days under ${money(v.limit)}. Latest: ${(v.last_days || []).map((x) => money(x)).join(", ")}.</p>` : ""}
      ${v.expected_by ? `<p class="small">Expected by ${dayLong(v.expected_by)}.</p>` : ""}
    </div>`;
  }

  function ownerHtml(d) {
    const trail = (d.evidence || {}).owner_trail;
    const src = OWNER_SOURCE[d.owner_source] || d.owner_source;
    const logName = d.provider === "aws" ? "AWS CloudTrail" : "Azure Activity Log";
    let html = "";
    if (d.owner) {
      html = `<div class="trail">
        <div><b>Looked up the resource's first create event</b><span>${esc(src)}${trail && trail.event ? ` · <code class="code">${esc(trail.event)}</code>` : ""}${trail && trail.at ? ` · ${dayLong(String(trail.at).slice(0, 10))}` : ""}</span></div>
        <div class="hit"><b>${avatar(d.owner)} <span>${esc(d.owner)}</span></b><span>${d.owner_source === "tag" ? "Taken from the resource's owner tag." : "The identity that made the call. No tag needed."}</span></div>
        ${d.assignee && d.assignee.email === d.owner ? `<div><b>Matched to a CloudPulse user</b><span>Assigned automatically</span></div>` : ""}
      </div>`;
    } else if (d.resource_id && !d.governance) {
      html = `<div class="callout">No create event in the last 90 days of the ${logName}, and no <code class="code">owner</code> tag. The resource is probably older than that. A workspace owner can assign it by hand.</div>`;
    } else {
      html = `<p class="muted">This finding is about the whole workspace, so it goes to the workspace owners.</p>`;
    }
    return html + `<p style="margin-top:10px">Assigned to: ${person(d.assignee)}</p>`;
  }

  async function openFinding(id) {
    if (!id) return;
    let d;
    try { d = await api(`/api/findings/${id}?${wsq()}`); }
    catch (err) { toast(err.message); return; }
    drawerId = id;
    $("#drawer-kicker").textContent = [d.kind_label, d.type_label, d.provider_label, d.region].filter(Boolean).join(" · ");
    $("#drawer-title").textContent = d.title;

    const acts = d.actions || [];
    $("#drawer-actions").innerHTML = acts.map((a) =>
      `<button class="btn btn-sm ${a === "resolve" ? "btn-primary" : ""}" type="button" data-action="${a}">${ACTION_TEXT[a] || a}</button>`).join("");

    const yearly = !d.governance && d.kind !== "anomaly";
    $("#drawer-body").innerHTML = `
      <div>
        <div class="drawer-meta">${prio(d)}<span class="muted small">score ${d.priority_score}</span>${statusTag(d.status)}
          <span class="badge outline">${esc(d.severity)}</span><span class="badge outline">${pct(d.confidence)} confident</span>
          <span class="muted small">open ${Math.round(d.age_days)} days</span></div>
        <p style="margin-top:10px">${esc(d.summary)}</p>
        ${d.status_note ? `<p class="callout" style="margin-top:8px">${esc(d.status_note)}</p>` : ""}
        ${d.status === "snoozed" && d.snoozed_until ? `<p class="muted small" style="margin-top:6px">Snoozed until ${dayLong(d.snoozed_until)}</p>` : ""}
      </div>
      <div id="act-slot" hidden></div>
      <div class="fact-row">
        <div class="fact"><span>${d.kind === "anomaly" ? ((d.evidence || {}).ongoing ? "If it continues" : "One-off excess") : d.kind === "budget_risk" ? "Over budget by" : d.kind === "untagged_spend" ? "Unattributed" : "Estimated waste"}</span><b>${money(d.monthly_impact)}</b><span>${esc(d.impact_basis || "per month")}</span></div>
        ${yearly ? `<div class="fact"><span>If left for a year</span><b>${money(d.monthly_impact * 12, 0)}</b><span>${d.list_price_impact != null && Math.abs(d.list_price_impact - d.monthly_impact) > 0.01 ? `list price says ${money(d.list_price_impact)}/mo` : "same rate"}</span></div>`
          : d.kind === "anomaly" ? `<div class="fact"><span>On the day</span><b>+${money((d.evidence || {}).excess)}</b><span>above usual</span></div>`
          : `<div class="fact"><span>Confidence</span><b>${pct(d.confidence)}</b><span>${esc((d.evidence || {}).rule || "")}</span></div>`}
      </div>
      ${verificationHtml(d)}
      <div><h3>Evidence</h3>${evidenceHtml(d)}</div>
      ${d.cost_history && d.cost_history.length > 1 ? `<div><h3>Billed cost of this resource</h3><div id="cost-hist"></div></div>` : ""}
      <div><h3>Why ${esc(d.priority)}</h3>${priorityHtml(d)}</div>
      <div><h3>Owner</h3>${ownerHtml(d)}</div>
      ${d.fix && d.fix.length ? `<div>
        <h3>How to fix it</h3>
        ${d.fix.map((c, i) => `
          <div class="cmd">
            <header><span>${esc(c.label)}</span><button class="btn btn-sm" type="button" data-copy="${i}"><svg><use href="#i-copy"/></svg>Copy</button></header>
            <pre>${esc(c.cmd)}</pre>
          </div>`).join("")}
        <p class="callout" style="margin-top:10px">CloudPulse only reads your account. Run this yourself in ${d.provider === "aws" ? "AWS CloudShell" : "Azure Cloud Shell"}, then mark the finding fixed; the next syncs check the bill.</p>
      </div>` : ""}
      <div>
        <h3>History</h3>
        <div class="timeline">${d.events.slice().reverse().map((ev) => `
          <div class="tl"><span class="ic ${esc(ev.kind)}" aria-hidden="true">${EVENT_ICON[ev.kind] || "•"}</span>
            <div><p>${esc(ev.message)}</p><small>${esc(ev.actor)} · ${dayLong(ev.at.slice(0, 10))} ${ev.at.slice(11, 16)}</small></div></div>`).join("")}
        </div>
      </div>
      ${d.resource_id ? `<div>
        <h3>Resource ID</h3>
        <div class="cmd"><header><span>${esc(d.provider_label || "")} ID</span><button class="btn btn-sm" type="button" data-copy="id"><svg><use href="#i-copy"/></svg>Copy</button></header><pre>${esc(d.resource_id)}</pre></div>
        <p class="muted small" style="margin-top:8px">First seen ${dayLong(d.first_seen.slice(0, 10))} · last seen ${dayLong(d.last_seen.slice(0, 10))}${d.still_detected ? "" : " · no longer detected"}</p>
      </div>` : ""}
      ${!acts.length ? `<p class="muted small">${curWs() && curWs().kind === "demo" ? "The demo is read-only." : "Only a workspace owner or the assignee can act on this finding."}</p>` : ""}`;

    const body = $("#drawer-body");
    $$("[data-copy]", body).forEach((b) => b.onclick = () => copy(b.dataset.copy === "id" ? d.resource_id : d.fix[Number(b.dataset.copy)].cmd));
    $$("[data-close]", body).forEach((a) => a.addEventListener("click", closeDrawer));
    showDrawer(true);
    const v = d.verification;
    const drawCharts = () => {
      if (v && v.series_before) {
        beforeAfter($("#ba-chart"), {
          before: v.series_before, after: v.series_after || [], beforeAvg: v.before_daily, afterAvg: v.after_daily,
          fmt: money, fmtAxis: moneyAxis, fmtDate: dayShort, fmtDateLong: dayLong,
        });
      }
      if (d.cost_history && d.cost_history.length > 1) {
        const mark = d.resolved_at ? d.resolved_at.slice(0, 10) : null;
        bars($("#cost-hist"), {
          days: d.cost_history.map((r) => ({ date: r.date, values: { c: r.amount } })),
          groups: [{ key: "c", label: "Cost", color: "var(--s1)" }], marker: mark ? { date: mark, label: "Marked fixed" } : null, height: 150,
          fmt: money, fmtAxis: moneyAxis, fmtDate: dayShort, fmtDateLong: dayLong, label: "Daily cost of this resource",
        });
      }
    };
    requestAnimationFrame(drawCharts);
    $("#drawer-close").focus();

    $("#drawer-actions").onclick = (e) => {
      const b = e.target.closest("[data-action]");
      if (b) actionForm(d, b.dataset.action);
    };
  }

  function actionForm(d, action) {
    const slot = $("#act-slot");
    const needsNote = action === "dismiss" || action === "comment";
    const people = d.assignable || [];
    slot.hidden = false;
    slot.innerHTML = `
      <form class="act-form" id="act-form">
        <b>${ACTION_TEXT[action]}</b>
        ${action === "assign" ? `<label class="field"><span>Assign to</span><select id="act-who">${people.map((p) =>
          `<option value="${p.id}" ${d.assignee && d.assignee.id === p.id ? "selected" : ""}>${esc(p.name)} · ${esc(p.email)} (${p.role})</option>`).join("")}</select></label>` : ""}
        ${action === "snooze" ? `<label class="field"><span>For how long</span><select id="act-days">${[7, 14, 30, 60, 90].map((n) => `<option value="${n}">${n} days</option>`).join("")}</select></label>` : ""}
        <label class="field"><span>${action === "dismiss" ? "Why is this not a problem? (required)" : action === "comment" ? "Comment" : "Note (optional)"}</span>
          <textarea id="act-note" maxlength="2000" placeholder="${action === "resolve" ? "What did you change?" : action === "dismiss" ? "e.g. Reserved for the October launch" : ""}"></textarea></label>
        ${action === "resolve" ? `<p class="muted small">CloudPulse will check on the next sync that the problem is gone, then compare the bill 7 days before and after.</p>` : ""}
        ${action === "dismiss" ? `<p class="muted small">Dismissed findings stay dismissed on later syncs. Anyone can see the reason.</p>` : ""}
        <p class="form-error" hidden></p>
        <div class="row"><button class="btn btn-sm" type="button" id="act-cancel">Cancel</button><button class="btn btn-sm btn-primary" type="submit">${ACTION_TEXT[action]}</button></div>
      </form>`;
    if (action === "assign" && !people.length) {
      slot.querySelector(".form-error").textContent = "No one else has access to this workspace yet. An admin can add people.";
      slot.querySelector(".form-error").hidden = false;
    }
    const noteEl = $("#act-note", slot);
    (($("#act-who", slot)) || noteEl).focus();
    slot.scrollIntoView({ block: "nearest" });
    $("#act-cancel", slot).onclick = () => { slot.hidden = true; slot.innerHTML = ""; };
    $("#act-form", slot).onsubmit = async (e) => {
      e.preventDefault();
      const note = noteEl.value.trim();
      const err = slot.querySelector(".form-error");
      if (needsNote && !note) { err.textContent = action === "dismiss" ? "Add a reason so others know why." : "Write something first."; err.hidden = false; return; }
      const payload = { action, note };
      if (action === "assign") payload.assignee_id = Number($("#act-who", slot).value);
      if (action === "snooze") payload.snooze_days = Number($("#act-days", slot).value);
      try {
        await postJSON(`/api/findings/${d.id}/action?${wsq()}`, payload);
        toast({ assign: "Assigned", start: "Marked in progress", resolve: "Marked fixed. The next sync will check it.", dismiss: "Dismissed",
          snooze: "Snoozed", reopen: "Reopened", comment: "Comment added" }[action]);
        await openFinding(d.id);
        refreshPage();
        loadNotifications();
      } catch (ex) { err.textContent = ex.message; err.hidden = false; }
    };
    // Quick actions with nothing to fill in go straight through on Enter/click of submit.
    if (action === "start" || action === "reopen") noteEl.placeholder = "Optional";
  }

  // ================================================================ anomalies
  async function renderAnomalies(root) {
    const [o, list] = await Promise.all([
      api(`/api/overview?${wsq({ days: 90 })}`),
      api(`/api/findings?${wsq({ status: "all", kind: "anomaly" })}`),
    ]);
    S.currency = o.currency || S.currency;
    applyPlain(o);
    const details = await Promise.all(list.items.map((x) => api(`/api/findings/${x.id}?${wsq()}`)));
    details.sort((a, b) => (b.evidence.date || "").localeCompare(a.evidence.date || ""));
    const open = details.filter((d) => ["open", "assigned", "in_progress", "snoozed"].includes(d.status)).length;
    setCounts(null, open);
    const firstBilled = o.series.findIndex((s) => s.amount > 0);
    const series = firstBilled > 0 ? o.series.slice(firstBilled) : o.series;
    const anomalySet = new Set(details.map((d) => d.evidence.date));

    root.innerHTML = `
      <section class="grid g-4">
        <div class="card kpi"><div class="kpi-label">Anomalies tracked</div><div class="kpi-value num">${details.length}</div><div class="kpi-sub">${open} still open</div></div>
        <div class="card kpi"><div class="kpi-label">Excess on those days</div><div class="kpi-value num">${money(details.reduce((s, d) => s + (d.evidence.excess || 0), 0))}</div><div class="kpi-sub">above the usual for each day</div></div>
        <div class="card kpi"><div class="kpi-label">Still running high</div><div class="kpi-value num">${details.filter((d) => d.evidence.ongoing && d.status !== "verified").length}</div><div class="kpi-sub">cost hasn't come back down</div></div>
        <div class="card kpi"><div class="kpi-label">Back to normal</div><div class="kpi-value num">${details.filter((d) => d.status === "verified").length}</div><div class="kpi-sub">verified on the bill</div></div>
      </section>

      <section class="card">
        <div class="card-head"><div><h2>Last ${o.window.days} days</h2><p>Ringed days were flagged. Click a day with a ring to open it.</p></div></div>
        <div class="card-body"><div id="an-all"></div></div>
      </section>

      <section class="card">
        <div class="card-head"><div><h2>How a day gets flagged</h2><p>Built to ignore normal weekly rhythm and single noisy days.</p></div></div>
        <div class="card-body">
          <div class="steps">
            <div class="step"><small>1 · Baseline</small><b>Same weekday, 4 weeks</b><p>Mondays are compared with Mondays. With fewer than 3, the previous 14 days are used.</p></div>
            <div class="step"><small>2 · Spread</small><b>Median and MAD</b><p>Usual = median. Swing = 1.4826 × median absolute deviation, at least 5% of usual.</p></div>
            <div class="step"><small>3 · Test</small><b>z above 3.5</b><p>And at least $1 and 20% above usual, so tiny accounts don't page anyone.</p></div>
            <div class="step"><small>4 · Explain</small><b>Split the increase</b><p>Each service's share of the extra spend, then the resources behind it.</p></div>
          </div>
        </div>
      </section>

      <section class="card">
        ${details.length ? details.map((d, i) => {
          const e = d.evidence;
          return `
          <article class="anomaly">
            <div class="anomaly-main">
              <div style="display:flex;justify-content:space-between;gap:10px;align-items:center;flex-wrap:wrap">
                <p class="muted small">${fWeek.format(D(e.date))}</p>
                <span style="display:flex;gap:8px;align-items:center">${prio(d)}${statusTag(d.status)}</span>
              </div>
              <div style="display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin:4px 0 10px">
                <span class="big num">${money(e.amount)}</span>
                <span class="delta up">+${money(e.excess)} (${pct(e.excess / e.expected)})</span>
                <span class="muted small">usual ${money(e.expected)} · z ${e.z}</span>
              </div>
              <div id="an-${i}"></div>
              <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;margin-top:8px;flex-wrap:wrap">
                <span class="small">${d.assignee ? person(d.assignee) : '<span class="muted">Goes to workspace owners</span>'}</span>
                <button class="btn btn-sm" type="button" data-finding="${d.id}">Open finding <svg><use href="#i-arrow"/></svg></button>
              </div>
            </div>
            <div class="anomaly-side">
              <h3 style="margin-bottom:8px">What drove it</h3>
              ${(e.drivers || []).length ? `<table class="data" style="font-size:12.5px"><thead><tr><th>Service</th><th class="r">Usual</th><th class="r">That day</th><th class="r">Share</th></tr></thead><tbody>
                ${e.drivers.slice(0, 4).map((r) => `<tr><td class="clip" title="${esc(r.service)}">${esc(r.service)}</td><td class="r muted">${money(r.usual)}</td><td class="r">${money(r.amount)}</td><td class="r">${pct(r.share)}</td></tr>`).join("")}
              </tbody></table>` : `<p class="muted">The increase was spread thinly across services.</p>`}
              ${d.verification ? `<p class="small" style="margin-top:10px">${d.verification.state === "verified" ? `<span class="badge good">Back to normal</span> ${esc(d.verification.method || "")}` : `<span class="badge warn">Watching</span> ${esc(d.verification.message || "")}`}</p>` : ""}
            </div>
          </article>`;
        }).join("") : `<div class="empty"><h3>No anomalies</h3><p>Spend has stayed close to its weekly pattern over the last 90 days.</p></div>`}
      </section>`;

    const draw = () => {
      bars($("#an-all"), {
        days: series.map((s) => ({ date: s.date, values: { t: s.amount } })),
        groups: [{ key: "t", label: "Spend", color: "var(--s1)" }], anomalies: anomalySet,
        ref: { value: o.daily_average }, height: 200,
        fmt: money, fmtAxis: moneyAxis, fmtDate: dayShort, fmtDateLong: dayLong, label: "Daily spend, 90 days",
        onClick: (day) => { const d = details.find((x) => x.evidence.date === day.date); if (d) openFinding(d.id); },
      });
      details.forEach((d, i) => {
        const idx = series.findIndex((s) => s.date === d.evidence.date);
        if (idx < 0) { $(`#an-${i}`).innerHTML = ""; return; }
        const from = Math.max(0, idx - 14), to = Math.min(series.length, idx + 6);
        bars($(`#an-${i}`), {
          days: series.slice(from, to).map((s) => ({ date: s.date, values: { t: s.amount } })),
          groups: [{ key: "t", label: "Spend", color: "var(--s1)" }],
          highlight: d.evidence.date, ref: { value: d.evidence.expected }, height: 150,
          fmt: money, fmtAxis: moneyAxis, fmtDate: dayShort, fmtDateLong: dayLong,
          label: `Spend around ${dayLong(d.evidence.date)}`,
        });
      });
    };
    draw();
    redraw = draw;
    root.onclick = (ev) => { const b = ev.target.closest("[data-finding]"); if (b) openFinding(Number(b.dataset.finding)); };
  }

  // ================================================================ budgets
  async function renderBudgets(root, page) {
    const [m, risk] = await Promise.all([
      api(`/api/month?${q()}`),
      api(`/api/findings?${wsq({ status: "all", kind: "budget_risk" })}`),
    ]);
    applyMeta(m, page);
    const f = m.forecast;
    const b = m.budget;
    const ratio = b ? f.forecast / b : null;
    const done = !f.days_remaining;
    const status = !b ? "" : ratio > 1 ? `<span class="badge bad">${done ? "Went over" : "Heading over"}</span>` : f.high > b ? `<span class="badge warn">Could go over</span>` : ratio > 0.85 ? `<span class="badge warn">Close to limit</span>` : `<span class="badge good">On track</span>`;
    const md = f.model || {};
    const wf = md.weekday_factors || null;
    const riskRow = risk.items.find((x) => x.status !== "verified" && x.status !== "dismissed") || risk.items[0];

    root.innerHTML = `
      <section class="card">
        <div class="card-head">
          <div><h2>Monthly budget</h2><p>One limit for this workspace. When the forecast passes it, a Budget risk finding is raised for the workspace owners.</p></div>
          ${status}
        </div>
        <div class="card-body">
          ${canEdit() ? "" : `<p class="muted" style="margin-bottom:10px">Only a workspace owner can change the budget.</p>`}
          <form class="budget-form" id="budget-form" ${canEdit() ? "" : "hidden"}>
            <label class="money-input"><span>$</span><input id="budget-input" type="number" min="0" step="1" inputmode="decimal" placeholder="e.g. 3000" value="${b ?? ""}" aria-label="Monthly budget in ${S.currency}"></label>
            <button class="btn btn-primary" type="submit">Save budget</button>
            ${b ? `<button class="btn" type="button" id="budget-clear">Remove</button>` : ""}
            <span class="muted small">${b ? "Saving re-runs the checks." : `Tip: the current run rate suggests about ${money(f.run_rate * 30.4, 0)}.`}</span>
          </form>
          ${riskRow ? `<p style="margin-top:12px"><button class="linkbtn" type="button" data-finding="${riskRow.id}">${prio(riskRow)}&nbsp; ${esc(riskRow.title)} · ${esc(STATUS_TEXT[riskRow.status])} <svg><use href="#i-arrow"/></svg></button></p>` : ""}
        </div>
      </section>

      <section class="grid g-4">
        <div class="card kpi"><div class="kpi-label">Budget</div><div class="kpi-value num">${b ? money(b, 0) : "—"}</div><div class="kpi-sub">${esc(f.month_label)}</div></div>
        <div class="card kpi"><div class="kpi-label">Spent so far</div><div class="kpi-value num">${money(f.month_to_date)}</div><div class="kpi-sub">${b ? `${pct(f.month_to_date / b)} of budget` : "Month to date"}</div></div>
        <div class="card kpi"><div class="kpi-label">${done ? "Month total" : "Forecast"}</div><div class="kpi-value num">${money(f.forecast)}</div><div class="kpi-sub">${done ? "Month complete" : `80% range ${money(f.low, 0)}–${money(f.high, 0)}`}</div></div>
        <div class="card kpi"><div class="kpi-label">${b ? (f.forecast > b ? "Over by" : "Headroom") : "Run rate"}</div><div class="kpi-value num" style="${b && f.forecast > b ? "color:var(--bad)" : ""}">${b ? money(Math.abs(b - f.forecast)) : money(f.run_rate)}</div><div class="kpi-sub">${b ? (f.breach_date ? `passes the budget on ${dayLong(f.breach_date)}` : done ? "Left unspent" : "Projected below budget") : "a day, last 7 billed days"}</div></div>
      </section>

      <section class="card">
        <div class="card-head"><div><h2>${esc(f.month_label)}, day by day</h2><p>Cumulative spend, then the forecast path with its 80% range.</p></div></div>
        <div class="card-body">
          <div class="legend">
            <span><i class="swatch" style="background:var(--s1)"></i>Spent</span>
            ${f.days_remaining ? `<span><i class="dot-key"></i>Forecast</span><span><i class="band-key"></i>80% range</span>` : ""}
            ${b ? `<span><i class="dash" style="border-color:var(--ink)"></i>Budget</span>` : ""}
            ${f.breach_date ? `<span><i class="breach-key"></i>Budget passed</span>` : ""}
          </div>
          <div id="cum"></div>
        </div>
      </section>

      <section class="card">
        <div class="card-head"><div><h2>How the forecast is made</h2><p>${esc(f.method)}</p></div></div>
        <div class="card-body grid g-2" style="gap:18px">
          <div class="math">
            ${md.alpha != null ? `
            <div class="ln"><span>level smoothing α</span><span>${md.alpha}</span></div>
            <div class="ln"><span>trend smoothing β</span><span>${md.beta}</span></div>
            <div class="ln"><span>current level</span><span>${money(md.level)} a day</span></div>
            <div class="ln"><span>trend</span><span>${md.trend_per_day >= 0 ? "+" : ""}${money(md.trend_per_day)} a day, each day</span></div>
            <div class="ln"><span>fit error (RMSE)</span><span>${money(md.rmse)}</span></div>
            <div class="ln"><span>days learned from</span><span>${f.billed_days_used}</span></div>
            <div class="ln total"><span>80% range</span><span>± 1.2816 × RMSE × √days left</span></div>`
            : `<div class="ln"><span>days learned from</span><span>${f.billed_days_used}</span></div>
               <div class="ln"><span>daily run rate</span><span>${money(f.run_rate)}</span></div>
               <div class="ln total"><span>method</span><span>${esc(f.method)}</span></div>`}
          </div>
          <div>
            <p class="small" style="color:var(--ink-2)">α and β are picked by testing 12 combinations and keeping the one with the smallest one-day-ahead error. With four weeks of history, each weekday gets its own factor, so quiet weekends don't drag the forecast down.</p>
            ${wf ? `<div class="bar-list" style="margin-top:12px">${Object.entries(wf).map(([k, v]) => `
              <div class="item" style="grid-template-columns:36px minmax(0,1fr) 40px;align-items:center"><span class="name">${k}</span><span class="track" style="grid-column:auto"><i style="width:${(v / 1.5) * 100}%"></i></span><span class="val">${v.toFixed(2)}</span></div>`).join("")}</div>` : ""}
          </div>
        </div>
      </section>`;

    const draw = () => cumulative($("#cum"), {
      path: f.path, budget: b, low: f.low, high: f.high, breach: f.breach_date,
      fmt: money, fmtAxis: moneyAxis, fmtDate: dayShort, fmtDateLong: dayLong,
    });
    draw();
    redraw = draw;
    root.onclick = (ev) => { const x = ev.target.closest("[data-finding]"); if (x) openFinding(Number(x.dataset.finding)); };

    $("#budget-form").onsubmit = async (ev) => {
      ev.preventDefault();
      const v = Number($("#budget-input").value);
      if (!(v > 0)) { toast("Enter an amount above zero."); return; }
      await postJSON(`/api/budget?${wsq()}`, { amount: v });
      toast("Budget saved. Checking it now.");
      watchSync();
      refreshPage();
    };
    const clear = $("#budget-clear");
    if (clear) clear.onclick = async () => {
      await postJSON(`/api/budget?${wsq()}`, { amount: 0 });
      toast("Budget removed");
      watchSync();
      refreshPage();
    };
  }

  // ================================================================ owners
  async function renderOwners(root) {
    const r = await api(`/api/owners?${wsq()}`);
    applyPlain(r);
    const people = r.owners;
    const named = people.filter((p) => p.owner);
    const fromLog = people.filter((p) => ["activity_log", "cloudtrail"].includes(p.source)).length;
    const totalOpen = people.reduce((s, p) => s + p.open_monthly, 0);
    const unowned = people.find((p) => !p.owner);

    root.innerHTML = `
      <section class="grid g-4">
        <div class="card kpi"><div class="kpi-label">People with findings</div><div class="kpi-value num">${named.length}</div><div class="kpi-sub">${curWs() && curWs().kind === "demo" ? "example records in the demo" : `${fromLog} found through audit logs`}</div></div>
        <div class="card kpi"><div class="kpi-label">Open, with an owner</div><div class="kpi-value num">${money(totalOpen - (unowned ? unowned.open_monthly : 0))}</div><div class="kpi-sub">of ${money(totalOpen)} a month</div></div>
        <div class="card kpi"><div class="kpi-label">No owner found</div><div class="kpi-value num">${unowned ? unowned.open : 0}</div><div class="kpi-sub">${unowned ? `${money(unowned.open_monthly)} a month` : "Every finding has someone"}</div></div>
        <div class="card kpi"><div class="kpi-label">Verified by people</div><div class="kpi-value num">${money(people.reduce((s, p) => s + p.verified_monthly, 0))}</div><div class="kpi-sub">a month</div></div>
      </section>

      <section class="card">
        <div class="owner-row head"><span>Person</span><span>Open</span><span>Verified saving</span><span>Days to fix</span><span>Open findings</span></div>
        <div class="owner-list">
          ${people.length ? people.map((p) => `
            <div class="owner-row">
              <div style="display:flex;gap:10px;align-items:center;min-width:0">${avatar(p.owner)}
                <div style="min-width:0"><div class="cell-main" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${esc(p.owner || "")}">${p.owner ? esc(p.owner) : "No owner found"}</div>
                <div class="src-tag">${p.owner ? `via ${esc(OWNER_SOURCE[p.source] || p.source || "")}` : "created before the audit window, untagged"}${p.assignee && p.assignee.email === p.owner ? " · has a CloudPulse login" : ""}</div></div></div>
              <div class="stat main"><b>${money(p.open_monthly)}</b><small>${p.open} finding${p.open === 1 ? "" : "s"}</small></div>
              <div class="stat"><b style="${p.verified_monthly ? "color:var(--good)" : ""}">${money(p.verified_monthly)}</b><small>${p.verified} verified</small></div>
              <div class="stat"><b>${p.median_days_to_fix != null ? `${p.median_days_to_fix}` : "—"}</b><small>median days</small></div>
              <div class="items">${p.findings.map((x) => `<button type="button" data-finding="${x.id}" title="${esc(x.kind)} · ${money(x.monthly)}">${esc(x.priority)} · ${esc(x.title)}</button>`).join("") || '<span class="muted small">Nothing open</span>'}</div>
            </div>`).join("") : `<div class="empty"><h3>No findings yet</h3><p>Owners appear once something is flagged.</p></div>`}
        </div>
      </section>

      <section class="card">
        <div class="card-head"><div><h2>How CloudPulse finds an owner</h2><p>Tags get forgotten, so the cloud's own audit trail comes first.</p></div></div>
        <div class="card-body">
          <div class="steps">
            <div class="step"><small>Step 1</small><b>Read the audit log</b><p>Azure Activity Log (90 days): the earliest accepted <code>…/write</code> on the resource.</p></div>
            <div class="step"><small>Step 2</small><b>Name the caller</b><p>A person's sign-in, or “service identity” for pipelines and managed identities.</p></div>
            <div class="step"><small>Step 3</small><b>Fall back to tags</b><p>If the log has nothing, an <code>owner</code>, <code>created-by</code> or <code>team</code> tag.</p></div>
            <div class="step"><small>Step 4</small><b>Assign automatically</b><p>If that person has a CloudPulse login, the finding lands in their queue and they're notified.</p></div>
          </div>
        </div>
      </section>`;
    root.onclick = (ev) => { const b = ev.target.closest("[data-finding]"); if (b) openFinding(Number(b.dataset.finding)); };
  }

  // ================================================================ savings
  async function renderSavings(root) {
    const r = await api(`/api/savings?${wsq()}`);
    applyPlain(r);
    const L = r.ledger;
    const total = L.open_estimated_monthly + L.resolved_pending + L.verified_monthly;
    const w = (v) => (total ? (v / total) * 100 : 0);
    const maxMonth = Math.max(1, ...L.by_month.map((m) => m.realized_monthly));
    const monthName = (k) => new Intl.DateTimeFormat("en-GB", { month: "short", year: "numeric" }).format(D(`${k}-01`));

    root.innerHTML = `
      <section class="card ledger-hero">
        <div>
          <p class="muted small" style="font-weight:600;letter-spacing:.05em;text-transform:uppercase">Verified savings</p>
          <div class="big" style="color:${L.verified_monthly ? "var(--good)" : "var(--ink)"}">${money(L.verified_monthly)}<span class="muted" style="font-size:16px;font-weight:400"> a month</span></div>
          <p style="margin-top:6px;color:var(--ink-2)">${L.verified_count} fix${L.verified_count === 1 ? "" : "es"} confirmed on the bill · ${money(L.saved_to_date)} saved so far · ${money(L.verified_monthly * 12, 0)} a year at this rate</p>
          ${L.accuracy != null ? `<p class="accuracy" style="margin-top:10px"><b>${pct(L.accuracy)}</b><span class="muted small">of what CloudPulse estimated actually came off the bill</span></p>` : ""}
        </div>
        <div>
          <div class="stack-bar" aria-hidden="true">
            <i style="width:${w(L.verified_monthly)}%;background:var(--s3)"></i>
            <i style="width:${w(L.resolved_pending)}%;background:var(--s4)"></i>
            <i style="width:${w(L.open_estimated_monthly)}%;background:var(--s-other)"></i>
          </div>
          <div class="legend" style="margin:10px 0 0;display:grid;gap:6px">
            <span><i class="swatch" style="background:var(--s3)"></i>Verified <b>${money(L.verified_monthly)}</b></span>
            <span><i class="swatch" style="background:var(--s4)"></i>Fixed, being checked <b>${money(L.resolved_pending)}</b></span>
            <span><i class="swatch" style="background:var(--s-other)"></i>Still open (estimate) <b>${money(L.open_estimated_monthly)}</b></span>
          </div>
        </div>
      </section>

      <section class="grid g-main">
        <div class="card">
          <div class="card-head"><div><h2>Verified fixes</h2><p>Estimate before the fix against what the bill showed after.</p></div></div>
          <div class="table-wrap" style="margin-top:12px">
            <table class="data">
              <thead><tr><th>Finding</th><th class="hide-sm">Fixed by</th><th class="r">Estimate</th><th class="r">Actual</th><th class="r hide-sm">Accuracy</th><th class="r hide-sm">Saved so far</th></tr></thead>
              <tbody>${r.verified.length ? r.verified.map((x) => `
                <tr class="clickable" data-finding="${x.id}" tabindex="0">
                  <td><div class="cell-main">${esc(x.resource_name || x.title)}</div><div class="cell-sub">${esc(x.kind_label)} · verified ${dayShort(x.verified_at.slice(0, 10))}${x.before_daily != null ? ` · ${money(x.before_daily)} → ${money(x.after_daily)} a day` : ""}</div></td>
                  <td class="hide-sm">${person(x.assignee)}</td>
                  <td class="r muted">${money(x.monthly_impact)}</td>
                  <td class="r"><b style="color:var(--good);font-weight:500">${money(x.realized_monthly)}</b></td>
                  <td class="r hide-sm">${x.accuracy != null ? pct(x.accuracy) : "—"}</td>
                  <td class="r hide-sm">${money(x.saved_to_date)}</td>
                </tr>`).join("") : `<tr><td colspan="6"><div class="empty"><h3>Nothing verified yet</h3><p>Mark a finding fixed; CloudPulse checks the bill over the following week.</p></div></td></tr>`}
              </tbody>
            </table>
          </div>
        </div>

        <div class="card">
          <div class="card-head"><div><h2>By month</h2><p>Monthly saving from fixes verified that month</p></div></div>
          <div class="card-body">
            <div class="bar-list">${L.by_month.length ? L.by_month.map((m) => `
              <div class="item"><span class="name">${monthName(m.month)}</span><span class="val">${money(m.realized_monthly)}</span><span class="track"><i style="width:${(m.realized_monthly / maxMonth) * 100}%;background:var(--s3)"></i></span></div>`).join("") : '<p class="muted">No months yet.</p>'}
            </div>
            <h3 style="font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--ink-3);margin:18px 0 8px">By person</h3>
            <div class="feed">${r.by_person.length ? r.by_person.map((p) => `
              <div class="feed-row" style="grid-template-columns:auto minmax(0,1fr) auto;column-gap:10px">
                <span style="grid-row:1 / span 2">${avatar(p.who)}</span>
                <span class="feed-title" style="grid-column:2">${esc(p.who)}</span>
                <span class="feed-val" style="grid-column:3">${money(p.verified_monthly)}</span>
                <span class="feed-meta" style="grid-column:2">${p.verified} fix${p.verified === 1 ? "" : "es"}</span>
              </div>`).join("") : '<p class="muted">No one yet.</p>'}</div>
          </div>
        </div>
      </section>

      ${r.pending.length ? `
      <section class="card">
        <div class="card-head"><div><h2>Fixed, waiting for the bill</h2><p>Not counted until the cost drop shows up.</p></div></div>
        <div class="table-wrap" style="margin-top:12px"><table class="data"><tbody>
          ${r.pending.map((x) => `<tr class="clickable" data-finding="${x.id}" tabindex="0">
            <td><div class="cell-main">${esc(x.resource_name || x.title)}</div><div class="cell-sub">${esc(x.kind_label)} · marked fixed ${x.resolved_at ? dayShort(x.resolved_at.slice(0, 10)) : ""}</div></td>
            <td class="hide-sm">${person(x.assignee)}</td>
            <td class="muted small">${esc((x.verification && x.verification.message) || "Checked on the next sync")}</td>
            <td class="r">${money(x.monthly_impact)} <span class="muted small">est.</span></td></tr>`).join("")}
        </tbody></table></div>
      </section>` : ""}

      <section class="card">
        <div class="card-head"><div><h2>How a saving is verified</h2><p>No saving is counted on someone's word.</p></div></div>
        <div class="card-body">
          <div class="steps">
            <div class="step"><small>1 · Fixed</small><b>Someone marks it fixed</b><p>With a note of what they changed.</p></div>
            <div class="step"><small>2 · Gone</small><b>Next sync confirms</b><p>If the problem is still there 30 minutes later, the finding reopens.</p></div>
            <div class="step"><small>3 · Measured</small><b>7 days before vs after</b><p>(avg before − avg after) × 30.4 = monthly saving, from the resource's own billed cost.</p></div>
            <div class="step"><small>4 · Kept honest</small><b>Regressions withdraw it</b><p>If the resource comes back, the saving is removed and the finding reopens.</p></div>
          </div>
        </div>
      </section>`;

    const open = (el) => openFinding(Number(el.dataset.finding));
    root.onclick = (ev) => { const t = ev.target.closest("[data-finding]"); if (t) open(t); };
    root.onkeydown = (ev) => { if (ev.key === "Enter") { const t = ev.target.closest("[data-finding]"); if (t) open(t); } };
  }

  // ================================================================ audit
  async function renderAudit(root) {
    const rows = await api("/api/admin/audit?limit=500");
    setControls("none");
    setBanner(null, null);
    const actions = [...new Set(rows.map((r) => r.action))].sort();
    let qy = "", act = "all";
    root.innerHTML = `
      <section class="card">
        <div class="table-tools">
          <label class="search"><svg><use href="#i-search"/></svg><span class="sr-only">Search</span><input id="au-q" type="search" placeholder="Search person, target, IP"></label>
          <label><span class="sr-only">Action</span><select class="filter-sel" id="au-act"><option value="all">All actions</option>${actions.map((a) => `<option>${esc(a)}</option>`).join("")}</select></label>
          <span class="muted small" id="au-count"></span>
          <button class="btn btn-sm" id="au-csv" type="button" style="margin-left:auto"><svg><use href="#i-download"/></svg>CSV</button>
        </div>
        <div class="table-wrap"><table class="data">
          <thead><tr><th>When</th><th>Who</th><th>Action</th><th class="hide-sm">Target</th><th class="hide-sm">Workspace</th><th class="hide-sm">IP</th></tr></thead>
          <tbody id="au-body"></tbody>
        </table></div>
      </section>`;
    const fmtT = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
    let shown = rows;
    const fill = () => {
      const s = qy.toLowerCase();
      shown = rows.filter((r) => (act === "all" || r.action === act) && (!s || [r.actor, r.target, r.ip, r.workspace, r.detail].some((v) => String(v || "").toLowerCase().includes(s))));
      $("#au-count").textContent = `${shown.length} of ${rows.length}`;
      $("#au-body").innerHTML = shown.length ? shown.map((r) => `<tr>
        <td class="muted" style="white-space:nowrap">${fmtT.format(D(r.at))}</td>
        <td>${esc(r.actor || "system")}</td>
        <td><span class="audit-action">${esc(r.action)}</span>${r.detail ? `<div class="cell-sub clip" title="${esc(r.detail)}">${esc(r.detail)}</div>` : ""}</td>
        <td class="hide-sm clip" title="${esc(r.target || "")}">${esc(r.target || "")}</td>
        <td class="hide-sm">${esc(r.workspace || "")}</td>
        <td class="hide-sm muted mono">${esc(r.ip || "")}</td></tr>`).join("")
        : `<tr><td colspan="6"><div class="empty"><h3>Nothing matches</h3></div></td></tr>`;
    };
    fill();
    $("#au-q").oninput = (e) => { qy = e.target.value; fill(); };
    $("#au-act").onchange = (e) => { act = e.target.value; fill(); };
    $("#au-csv").onclick = () => {
      const cell = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
      download("cloudpulse-audit.csv", ["at,actor,action,target,workspace,ip,detail"].concat(shown.map((r) => [r.at, r.actor, r.action, r.target, r.workspace, r.ip, r.detail].map(cell).join(","))).join("\n"), "text/csv");
    };
  }

  // ================================================================ sources
  const LOGO = { azure: '<span class="logo azure">Az</span>', aws: '<span class="logo aws">AWS</span>' };
  function statusBadge(st) {
    const s = (st && st.state) || "not_synced";
    if (s === "connected") return `<span class="badge good">Connected</span>`;
    if (s === "error") return `<span class="badge bad">Can't connect</span>`;
    if (s === "demo") return `<span class="badge">Demo</span>`;
    return `<span class="badge">Not synced yet</span>`;
  }
  function connProblems(st) {
    if (!st) return "";
    const lines = [];
    if (st.message) lines.push(st.message);
    if (st.cost_error) lines.push(`Spend: ${st.cost_error}`);
    if (st.leak_error) lines.push(`Resource scan: ${st.leak_error}`);
    return lines.map((l) => `<div class="err">${esc(l)}</div>`).join("");
  }

  async function renderSources(root) {
    const c = await api(`/api/connections?${wsq()}`);
    setControls("none");
    setBanner(null, c);
    setFoot(c);
    const w = curWs();
    const books = c.books || {};
    const bookRows = Object.entries(books).map(([k, v]) => `
      <tr><td class="cell-main">${k === "live" ? "From connected accounts" : v.dataset === "focus-sample" ? "FinOps Foundation sample bill" : esc(v.dataset || "Imported file")}</td>
      <td>${v.from ? `${dayLong(v.from)} – ${dayLong(v.to)}` : "—"}</td><td class="r">${v.rows.toLocaleString("en-IN")}</td></tr>`).join("");

    root.innerHTML = `
      <section class="card">
        <div class="card-head">
          <div><h2>Cloud accounts</h2><p>CloudPulse signs in with a read-only identity. It can't change or delete anything.</p></div>
          ${S.me.is_admin && w.kind !== "demo" ? `<a class="btn btn-sm" href="#/admin"><svg><use href="#i-plus"/></svg>Manage</a>` : ""}
        </div>
        <div class="card-body">
          ${w.kind === "demo" ? `<p class="muted">The demo workspace isn't connected to any cloud. It uses a fixed sample bill and example resources.</p>`
          : c.items.length ? `<div class="grid" style="gap:14px">${c.items.map((x) => `
            <div class="conn-row">
              ${LOGO[x.provider] || ""}
              <div>
                <div class="cell-main">${esc(x.label || x.provider)}</div>
                <div class="meta">${esc(x.auth)}${x.subscription_id ? ` · subscription ${esc(x.subscription_id)}` : ""}${x.region ? ` · ${esc(x.region)}` : ""}</div>
                ${x.status && x.status.identity ? `<div class="meta">Signed in as ${esc(x.status.identity)}</div>` : ""}
                ${connProblems(x.status)}
              </div>
              ${statusBadge(x.status)}
            </div>`).join("")}</div>`
          : `<div class="empty"><h3>No cloud account connected</h3><p>${S.me.is_admin ? 'Add one under <a href="#/admin">Workspaces &amp; users</a>.' : "Ask your CloudPulse administrator to connect your Azure subscription."}</p></div>`}
        </div>
        ${c.last_run ? `<div class="card-foot"><span class="muted small">Last sync ${ago(c.last_run)}</span></div>` : ""}
      </section>

      <section class="card source-card">
        <header><span class="logo focus">F</span><div><h2 style="font-size:15px">Imported bills (FOCUS)</h2><p class="muted small">The open billing format AWS, Azure, Google Cloud and Oracle can all export</p></div></header>
        ${bookRows ? `<div class="table-wrap"><table class="data"><thead><tr><th>Source</th><th>Covers</th><th class="r">Rows</th></tr></thead><tbody>${bookRows}</tbody></table></div>` : ""}
        ${canEdit() ? `
        <form class="drop" id="drop">
          <p><b>Import a FOCUS export.</b> CSV or .csv.gz, up to 50 MB. In Azure: Cost Management → Exports → “Cost and usage (FOCUS)”. It replaces this workspace's current imported bill.</p>
          <label class="btn" for="drop-input">Choose file</label>
          <input type="file" id="drop-input" accept=".csv,.gz" hidden>
          <span class="muted small" id="drop-status" role="status"></span>
        </form>` : `<p class="muted">${w.kind === "demo" ? "Imports are turned off in the demo." : "Only a workspace owner can import bills."}</p>`}
      </section>`;

    const drop = $("#drop");
    if (!drop) { redraw = null; return; }
    const input = $("#drop-input"), status = $("#drop-status");
    const upload = async (file) => {
      if (!file) return;
      status.textContent = `Reading ${file.name}…`;
      const fd = new FormData();
      fd.append("file", file);
      try {
        await api(`/api/focus?${wsq()}`, { method: "POST", body: fd });
        S.book = "focus";
        toast(`Imported ${file.name}`);
        location.hash = "#/overview";
      } catch (err) { status.textContent = `Couldn't import: ${err.message}`; }
    };
    input.onchange = () => upload(input.files[0]);
    ["dragenter", "dragover"].forEach((t) => drop.addEventListener(t, (e) => { e.preventDefault(); drop.classList.add("over"); }));
    ["dragleave", "drop"].forEach((t) => drop.addEventListener(t, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
    drop.addEventListener("drop", (e) => upload(e.dataTransfer.files[0]));
    redraw = null;
  }

  // ================================================================ generic drawer form
  function openPanel(kicker, title, html, wire) {
    lastFocus = document.activeElement;
    $("#drawer-kicker").textContent = kicker;
    $("#drawer-title").textContent = title;
    $("#drawer-body").innerHTML = html;
    $("#drawer").hidden = false;
    if (wire) wire($("#drawer-body"));
    const first = $("#drawer-body").querySelector("input, select, button");
    (first || $("#drawer-close")).focus();
  }
  function showSecret(title, who, password) {
    openPanel("Share this once", title, `
      <p>Send this temporary password to <b>${esc(who)}</b> privately (not in a group chat). They'll be asked to choose their own the first time they sign in.</p>
      <div class="secret-box"><span id="secret-value">${esc(password)}</span><button class="btn btn-sm" type="button" id="copy-secret"><svg><use href="#i-copy"/></svg>Copy</button></div>
      <p class="callout">CloudPulse doesn't keep this password in readable form, so it can't be shown again. If it's lost, reset it.</p>
      <div><button class="btn btn-primary" type="button" id="secret-done">Done</button></div>`,
    (body) => {
      $("#copy-secret", body).onclick = () => copy(password);
      $("#secret-done", body).onclick = () => { closeDrawer(); route(); };
    });
  }
  function formError(body, msg) {
    let el = body.querySelector(".form-error");
    el.textContent = msg;
    el.hidden = !msg;
  }

  // ================================================================ admin
  async function renderAdmin(root) {
    const d = await api("/api/admin/overview");
    setControls("none");
    setBanner(null, null);
    const customers = d.workspaces.filter((w) => w.kind !== "demo");
    const allConns = d.workspaces.flatMap((w) => w.connections);
    const failing = allConns.filter((c) => c.status && c.status.state === "error").length;

    const wsCard = (w) => `
      <article class="card ws-card">
        <header>
          <div>
            <h2>${esc(w.name)} ${w.kind === "demo" ? '<span class="badge">Demo</span>' : ""}</h2>
            <p class="muted small">/${esc(w.slug)} · ${w.last_run ? `synced ${ago(w.last_run)}` : "never synced"}</p>
          </div>
          <div class="actions">
            <button class="btn btn-sm" type="button" data-act="sync" data-ws="${w.id}" data-slug="${esc(w.slug)}"><svg><use href="#i-refresh"/></svg>Sync</button>
            ${w.kind !== "demo" ? `
              <button class="btn btn-sm" type="button" data-act="azure" data-ws="${w.id}"><svg><use href="#i-plus"/></svg>Connect Azure</button>
              <button class="btn btn-sm" type="button" data-act="person" data-ws="${w.id}"><svg><use href="#i-plus"/></svg>Add person</button>
              <button class="btn btn-sm" type="button" data-act="open" data-slug="${esc(w.slug)}">Open</button>
              ${w.connections.some((c) => c.auth.includes("server settings")) ? "" : `<button class="btn btn-sm" type="button" data-act="delws" data-ws="${w.id}" data-name="${esc(w.name)}">Delete</button>`}` : `<button class="btn btn-sm" type="button" data-act="open" data-slug="${esc(w.slug)}">Open</button>`}
          </div>
        </header>
        ${w.kind !== "demo" ? `
        <div class="ws-section">
          <h3>Cloud accounts</h3>
          ${w.connections.length ? w.connections.map((c) => `
            <div class="conn-row">
              ${LOGO[c.provider] || ""}
              <div>
                <div class="cell-main">${esc(c.label)}</div>
                <div class="meta">${esc(c.auth)}${c.subscription_id ? ` · ${esc(c.subscription_id)}` : ""}${c.secret_readable === false ? " · stored secret unreadable, re-add it" : ""}</div>
                ${c.status && c.status.identity ? `<div class="meta">Signed in as ${esc(c.status.identity)}</div>` : ""}
                ${connProblems(c.status)}
              </div>
              <div style="display:grid;gap:6px;justify-items:end">
                ${statusBadge(c.status)}
                ${c.auth.includes("server settings") ? '<span class="muted small">from server settings</span>' : `<button class="linkbtn" type="button" data-act="delconn" data-conn="${c.id}">Remove</button>`}
              </div>
            </div>`).join("") : `<p class="muted">Nothing connected yet. Use <b>Connect Azure</b>.</p>`}
        </div>` : ""}
        <div class="ws-section">
          <h3>People</h3>
          ${w.kind === "demo" ? `<p class="muted">Anyone can open the demo from the sign-in page. It's read-only.</p>` :
          w.members.length ? w.members.map((m) => `
            <div style="display:flex;align-items:center;gap:10px">${avatar(m.email)}<div style="min-width:0;flex:1"><div class="cell-main">${esc(m.name || m.email)}</div><div class="muted small">${esc(m.email)}</div></div>
            <span class="badge ${m.role === "owner" ? "good" : ""}">${m.role === "owner" ? "Owner" : "Viewer"}</span>${m.example ? '<span class="badge outline">Example</span>' : ""}</div>`).join("")
          : `<p class="muted">No one can sign in to this workspace yet. Use <b>Add person</b>.</p>`}
        </div>
      </article>`;

    root.innerHTML = `
      <section class="grid g-4">
        <div class="card kpi"><div class="kpi-label">Customer workspaces</div><div class="kpi-value num">${customers.length}</div><div class="kpi-sub">plus the demo</div></div>
        <div class="card kpi"><div class="kpi-label">Cloud connections</div><div class="kpi-value num">${allConns.length}</div><div class="kpi-sub">${failing ? `<span class="badge bad">${failing} failing</span>` : "All healthy"}</div></div>
        <div class="card kpi"><div class="kpi-label">People</div><div class="kpi-value num">${d.users.filter((u) => !u.is_demo).length}</div><div class="kpi-sub">${d.users.filter((u) => u.is_admin).length} admin</div></div>
        <div class="card kpi"><div class="kpi-label">Waiting to set a password</div><div class="kpi-value num">${d.users.filter((u) => u.must_change_password && !u.is_demo).length}</div><div class="kpi-sub">Signed in with a temporary one</div></div>
      </section>

      <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap">
        <h2 style="font-size:16px">Workspaces</h2>
        <button class="btn btn-primary" type="button" data-act="newws"><svg><use href="#i-plus"/></svg>New workspace</button>
      </div>
      <section class="grid g-2">${d.workspaces.map(wsCard).join("")}</section>

      <section class="card">
        <div class="card-head">
          <div><h2>People</h2><p>Everyone who can sign in. The demo account has no password.</p></div>
          <button class="btn btn-sm" type="button" data-act="person"><svg><use href="#i-plus"/></svg>Add person</button>
        </div>
        <div class="table-wrap" style="margin-top:12px">
          <table class="data">
            <thead><tr><th>Person</th><th>Type</th><th class="hide-sm">Workspaces</th><th class="hide-sm">Last sign-in</th><th class="r">Actions</th></tr></thead>
            <tbody>${d.users.map((u) => `
              <tr>
                <td><div style="display:flex;align-items:center;gap:10px">${avatar(u.email)}<div style="min-width:0"><div class="cell-main">${esc(u.name || u.email)}${u.id === S.me.id ? ' <span class="muted small">(you)</span>' : ""}</div><div class="cell-sub">${esc(u.email)}</div></div></div></td>
                <td>${u.is_admin ? '<span class="badge good">Admin</span>' : u.is_demo ? '<span class="badge">Demo</span>' : '<span class="badge outline">Customer</span>'}
                    ${u.disabled ? '<span class="badge bad">Disabled</span>' : u.must_change_password && !u.is_demo ? '<span class="badge warn">Temporary password</span>' : ""}</td>
                <td class="hide-sm">${u.is_admin ? '<span class="muted">All</span>' : u.workspaces.map((m) => `${esc(m.name)} <span class="muted">(${m.role})</span>`).join(", ") || '<span class="muted">None</span>'}</td>
                <td class="hide-sm muted">${u.last_login_at ? ago(u.last_login_at) : "Never"}</td>
                <td class="r">${u.is_demo || u.id === S.me.id ? "" : `
                  <button class="linkbtn" type="button" data-act="reset" data-user="${u.id}" data-email="${esc(u.email)}">Reset password</button>
                  <button class="linkbtn" type="button" data-act="${u.disabled ? "enable" : "disable"}" data-user="${u.id}" style="margin-left:10px">${u.disabled ? "Enable" : "Disable"}</button>`}</td>
              </tr>`).join("")}</tbody>
          </table>
        </div>
      </section>`;

    root.onclick = async (ev) => {
      const b = ev.target.closest("[data-act]");
      if (!b) return;
      const act = b.dataset.act;
      try {
        if (act === "open") { selectWorkspace(b.dataset.slug); location.hash = "#/overview"; }
        else if (act === "sync") {
          b.disabled = true; b.classList.add("spinning");
          const r = await postJSON(`/api/admin/workspaces/${b.dataset.ws}/sync`);
          toast("Sync started");
          b.disabled = false; b.classList.remove("spinning");
          if (String(b.dataset.slug || "") === S.ws) watchSync(r.run_id);
        }
        else if (act === "newws") newWorkspaceForm();
        else if (act === "azure") azureForm(d.workspaces.find((w) => w.id === Number(b.dataset.ws)));
        else if (act === "person") personForm(customers, b.dataset.ws ? Number(b.dataset.ws) : null);
        else if (act === "delconn") {
          if (!confirm("Remove this cloud connection? Data already collected stays until the workspace is deleted.")) return;
          await api(`/api/admin/connections/${b.dataset.conn}`, { method: "DELETE" });
          toast("Connection removed"); route();
        }
        else if (act === "delws") {
          if (!confirm(`Delete the workspace “${b.dataset.name}” and all its data? People lose access to it.`)) return;
          await api(`/api/admin/workspaces/${b.dataset.ws}`, { method: "DELETE" });
          toast("Workspace deleted"); await reloadMe(); route();
        }
        else if (act === "reset") {
          if (!confirm(`Give ${b.dataset.email} a new temporary password? Their current sessions end.`)) return;
          const r = await postJSON(`/api/admin/users/${b.dataset.user}/reset-password`);
          showSecret("New temporary password", b.dataset.email, r.temporary_password);
        }
        else if (act === "disable" || act === "enable") {
          await postJSON(`/api/admin/users/${b.dataset.user}/disabled`, { disabled: act === "disable" });
          toast(act === "disable" ? "Account disabled" : "Account enabled"); route();
        }
      } catch (err) { toast(err.message); b.disabled = false; b.classList.remove("spinning"); }
    };
    redraw = null;
  }

  function newWorkspaceForm() {
    openPanel("New workspace", "Add a customer", `
      <form class="form-grid" id="ws-form" novalidate>
        <p class="muted">A workspace holds one organisation's cloud accounts and data. People you add to it only ever see this workspace.</p>
        <label class="field"><span>Name</span><input id="ws-name" maxlength="80" placeholder="e.g. Tamilmani – Azure" required></label>
        <p class="form-error" hidden></p>
        <div><button class="btn btn-primary" type="submit">Create workspace</button></div>
      </form>`, (body) => {
      $("#ws-form", body).onsubmit = async (e) => {
        e.preventDefault();
        const name = $("#ws-name", body).value.trim();
        if (name.length < 2) return formError(body, "Give the workspace a name.");
        try {
          const r = await postJSON("/api/admin/workspaces", { name });
          await reloadMe();
          closeDrawer();
          toast("Workspace created. Next: connect its Azure subscription.");
          await route();
          azureForm({ id: r.id, name });
        } catch (err) { formError(body, err.message); }
      };
    });
  }

  function azureForm(w) {
    openPanel(w.name, "Connect an Azure subscription", `
      <form class="form-grid" id="az-form" novalidate autocomplete="off">
        <div class="callout">In Azure Cloud Shell, run <code class="code">bash scripts/azure/03-reader-identity.sh</code>. It creates a read-only identity and prints the four values below. The secret is stored encrypted and never shown again.</div>
        <label class="field"><span>Label</span><input id="az-label" value="Azure subscription" maxlength="80"></label>
        <label class="field"><span>Subscription ID</span><input id="az-sub" placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" required></label>
        <label class="field"><span>Tenant ID</span><input id="az-tenant" placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" required></label>
        <label class="field"><span>Client (app) ID</span><input id="az-client" placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" required></label>
        <label class="field"><span>Client secret</span><input id="az-secret" type="password" autocomplete="new-password" required></label>
        <p class="form-error" hidden></p>
        <div><button class="btn btn-primary" type="submit" id="az-submit">Connect and test</button></div>
      </form>`, (body) => {
      $("#az-form", body).onsubmit = async (e) => {
        e.preventDefault();
        const btn = $("#az-submit", body);
        btn.disabled = true; btn.textContent = "Connecting…";
        try {
          const r = await postJSON(`/api/admin/workspaces/${w.id}/azure`, {
            label: $("#az-label", body).value, subscription_id: $("#az-sub", body).value,
            tenant_id: $("#az-tenant", body).value, client_id: $("#az-client", body).value,
            client_secret: $("#az-secret", body).value,
          });
          if (r.status && r.status.state === "connected") { toast("Connected. The first sync is running."); closeDrawer(); await reloadMe(); route(); }
          else { formError(body, `Saved, but the test failed: ${(r.status && r.status.message) || "unknown error"}. Fix the values and add it again, then remove the old one.`); route(); }
        } catch (err) { formError(body, err.message); }
        finally { btn.disabled = false; btn.textContent = "Connect and test"; }
      };
    });
  }

  function personForm(customers, wsId) {
    openPanel("Add person", "Give someone access", `
      <form class="form-grid" id="person-form" novalidate autocomplete="off">
        <label class="field"><span>Email</span><input id="p-email" type="email" required></label>
        <label class="field"><span>Name <small>(optional)</small></span><input id="p-name" maxlength="80"></label>
        <fieldset class="field" style="border:0;padding:0;margin:0"><span>Type</span>
          <div class="radio-row">
            <label><input type="radio" name="p-type" value="customer" checked> Customer</label>
            <label><input type="radio" name="p-type" value="admin"> Administrator</label>
          </div>
        </fieldset>
        <div id="p-customer" class="form-grid">
          <label class="field"><span>Workspace</span>
            <select id="p-ws">${customers.map((w) => `<option value="${w.id}" ${w.id === wsId ? "selected" : ""}>${esc(w.name)}</option>`).join("")}</select>
          </label>
          <fieldset class="field" style="border:0;padding:0;margin:0"><span>Role</span>
            <div class="radio-row">
              <label><input type="radio" name="p-role" value="owner"> Owner <small class="muted">sync, budgets, imports</small></label>
              <label><input type="radio" name="p-role" value="viewer" checked> Viewer <small class="muted">look only</small></label>
            </div>
          </fieldset>
        </div>
        <p class="form-error" hidden></p>
        <div><button class="btn btn-primary" type="submit">Create account</button></div>
      </form>`, (body) => {
      const sync = () => { $("#p-customer", body).hidden = body.querySelector('input[name="p-type"]:checked').value === "admin"; };
      body.querySelectorAll('input[name="p-type"]').forEach((r) => r.onchange = sync);
      if (!customers.length) formError(body, "Create a customer workspace first, or add an administrator.");
      $("#person-form", body).onsubmit = async (e) => {
        e.preventDefault();
        const isAdmin = body.querySelector('input[name="p-type"]:checked').value === "admin";
        const email = $("#p-email", body).value.trim();
        try {
          const r = await postJSON("/api/admin/users", {
            email, name: $("#p-name", body).value, is_admin: isAdmin,
            workspace_id: isAdmin ? null : Number($("#p-ws", body).value),
            role: body.querySelector('input[name="p-role"]:checked').value,
          });
          showSecret("Account created", r.email, r.temporary_password);
        } catch (err) { formError(body, err.message); }
      };
    });
  }

  // ================================================================ account
  function openPasswordModal(force) {
    const m = $("#pw-modal");
    $("#pw-form").reset();
    $("#pw-error").hidden = true;
    $("#pw-cancel").hidden = force;
    $("#pw-title").textContent = force ? "Choose your own password" : "Change your password";
    $("#pw-intro").textContent = force
      ? "You signed in with a temporary password. Pick a new one to continue: at least 10 characters, with upper and lower case letters and a number."
      : "At least 10 characters, with upper and lower case letters and a number.";
    m.dataset.force = force ? "1" : "";
    m.hidden = false;
    $("#pw-current").focus();
  }
  $("#pw-cancel").onclick = () => { $("#pw-modal").hidden = true; };
  $("#pw-form").onsubmit = async (e) => {
    e.preventDefault();
    const err = $("#pw-error");
    const cur = $("#pw-current").value, nw = $("#pw-new").value, rep = $("#pw-repeat").value;
    err.hidden = true;
    if (nw !== rep) { err.textContent = "The two new passwords don't match."; err.hidden = false; return; }
    try {
      await postJSON("/api/auth/password", { current: cur, new: nw });
      $("#pw-modal").hidden = true;
      S.me.must_change_password = false;
      toast("Password changed. Other devices were signed out.");
    } catch (ex) { err.textContent = ex.message; err.hidden = false; }
  };
  $("#change-pw").onclick = () => openPasswordModal(false);
  $("#sign-out").onclick = async () => {
    try { await postJSON("/api/auth/logout"); } finally { location.replace("/login"); }
  };

  // ================================================================ boot
  function selectWorkspace(slug) {
    S.ws = slug;
    S.f = { status: "active", kind: "all", priority: "all", mine: false, q: "" };
    S.book = "auto";
    S.provider = "all";
    store.set("ws", slug);
    $("#ws-select").value = slug;
  }

  function renderUser() {
    const me = S.me;
    $("#user-avatar").innerHTML = avatar(me.is_demo ? "Demo Visitor" : me.email);
    $("#user-name").textContent = me.is_demo ? "Demo visitor" : (me.name || me.email);
    const w = curWs();
    $("#user-role").textContent = me.is_admin ? "Administrator" : me.is_demo ? "Read-only demo" : w ? (w.role === "owner" ? "Workspace owner" : "Workspace viewer") : "";
    $("#change-pw").hidden = me.is_demo;
    $("#sign-out").textContent = me.is_demo ? "Leave the demo" : "Sign out";
    $$("[data-admin]").forEach((el) => { el.hidden = !me.is_admin; });
    const sel = $("#ws-select");
    sel.innerHTML = me.workspaces.map((w) => `<option value="${esc(w.slug)}">${esc(w.name)}${w.kind === "demo" ? " (demo)" : ""}</option>`).join("");
    sel.value = S.ws || "";
    $("#ws-switch-wrap").hidden = me.workspaces.length < 2;
  }

  async function reloadMe() {
    S.me = await api("/api/auth/me");
    if (!S.me.workspaces.some((w) => w.slug === S.ws)) {
      const pick = S.me.workspaces.find((w) => w.kind !== "demo") || S.me.workspaces[0];
      S.ws = pick ? pick.slug : null;
    }
    renderUser();
  }

  $("#ws-select").onchange = (e) => { selectWorkspace(e.target.value); renderUser(); route(); loadCounts(); };

  async function boot() {
    try {
      S.me = await api("/api/auth/me");
    } catch { return; }
    const saved = store.get("ws", null);
    const valid = S.me.workspaces.find((w) => w.slug === saved);
    const pick = valid || S.me.workspaces.find((w) => w.kind !== "demo") || S.me.workspaces[0];
    S.ws = pick ? pick.slug : null;
    renderUser();
    if (S.me.must_change_password) openPasswordModal(true);
    if (!S.ws && !S.me.is_admin) {
      $("#page").innerHTML = `<div class="card empty"><h3>You don't have a workspace yet</h3><p>Ask your CloudPulse administrator to add you to one.</p></div>`;
      $("#controls").hidden = true;
      return;
    }
    if (!S.ws) location.hash = "#/admin";
    route();
    loadCounts();
    loadNotifications();
    setInterval(loadNotifications, 60000);
  }

  // ================================================================ global wiring
  let redraw = null;
  $("#book-switch").onclick = (e) => { const b = e.target.closest("[data-book]"); if (b) { S.book = b.dataset.book; S.provider = "all"; route(); } };
  $("#provider-select").onchange = (e) => { S.provider = e.target.value; route(); };
  $("#range-switch").onclick = (e) => { const b = e.target.closest("[data-days]"); if (b) { S.days = Number(b.dataset.days); store.set("days", S.days); route(); } };
  $("#refresh").onclick = async (e) => {
    const b = e.currentTarget;
    b.disabled = true; b.classList.add("spinning");
    try {
      const r = await postJSON(`/api/collect?${wsq()}`);
      if (r.status === "queued" || r.status === "running") watchSync(r.run_id);
      else { toast("Sync finished"); b.disabled = false; b.classList.remove("spinning"); await refreshPage(); }
    } catch (err) {
      toast(`Sync failed: ${err.message}`);
      b.disabled = false; b.classList.remove("spinning");
    }
  };

  const openNav = () => { $("#sidebar").classList.add("open"); $("#scrim").hidden = false; };
  function closeNav() { $("#sidebar").classList.remove("open"); $("#scrim").hidden = true; }
  $("#open-nav").onclick = openNav;
  $("#close-nav").onclick = closeNav;
  $("#scrim").onclick = closeNav;
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (!$("#notif-panel").hidden) toggleNotifications(false);
      else if (!$("#drawer").hidden) closeDrawer();
      else closeNav();
    }
  });

  let rt;
  window.addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(() => redraw && redraw(), 120); });
  window.addEventListener("hashchange", () => { if (!$("#drawer").hidden) closeDrawer(); route(); });
  window.addEventListener("scroll", () => tip.hide(), { passive: true });
  boot();
})();
