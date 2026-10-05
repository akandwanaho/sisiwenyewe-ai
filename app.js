(function () {
"use strict";

var API = "https://chatbot.sisiwenyewe.com";
var STORE = "sisiwenyewe_chats";
var FALLBACK = "Sorry, I can’t answer that at the moment. Please check again in the next few days as my training and knowledge base continue to improve.";

var $ = function (s) { return document.querySelector(s); };
var app = $("#app"), thread = $("#thread"), q = $("#q"), form = $("#composer"), sendBtn = $("#sendBtn"),
    historyEl = $("#history"), searchEl = $("#search"), micBtn = $("#micBtn");
var reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;

/* ---------- helpers ---------- */
function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
function svg(html, w) { var s = document.createElementNS("http://www.w3.org/2000/svg", "svg"); s.setAttribute("viewBox", "0 0 24 24"); s.setAttribute("width", w || 15); s.setAttribute("height", w || 15); s.setAttribute("fill", "none"); s.setAttribute("stroke", "currentColor"); s.setAttribute("stroke-width", "2"); s.setAttribute("stroke-linecap", "round"); s.setAttribute("stroke-linejoin", "round"); s.innerHTML = html; return s; }
var IC = {
  copy: '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>',
  check: '<path d="M5 12l5 5L20 7"/>',
  speak: '<path d="M11 5L6 9H3v6h3l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7M18.5 5.5a9 9 0 0 1 0 13"/>',
  retry: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>',
  doc: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>',
  ext: '<path d="M14 4h6v6M20 4l-9 9M19 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5"/>',
  wave: '<path d="M2 12h3l3-8 4 16 3-8h7"/>',
  trash: '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>',
  sensor: '<circle cx="12" cy="12" r="2"/><path d="M8.5 8.5a5 5 0 0 0 0 7M15.5 8.5a5 5 0 0 1 0 7M5.6 5.6a9 9 0 0 0 0 12.8M18.4 5.6a9 9 0 0 1 0 12.8"/>',
  shield: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
  brief: '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M3 13h18"/>',
  lock: '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
  shield: '<path d="M12 3l8 3v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6z"/><path d="M9 12l2 2 4-4"/>'
};
var MARK = '<svg viewBox="0 0 32 32" width="20" height="20"><circle cx="16" cy="16" r="3" fill="#F5C518"/><path d="M16 4a12 12 0 0 1 10.4 6l-6.9 4a4 4 0 0 0-3.5-2zM26.4 22a12 12 0 0 1-20.8 0l6.9-4a4 4 0 0 0 7 0zM5.6 10A12 12 0 0 1 16 4v8a4 4 0 0 0-3.5 2z" fill="#F5C518"/></svg>';
function toast(msg) { var t = $("#toast"); t.textContent = msg; t.classList.add("on"); clearTimeout(t._h); t._h = setTimeout(function () { t.classList.remove("on"); }, 3200); }
function timeStr(iso) { var d = iso ? new Date(iso) : new Date(); return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }); }
function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }

/* Safe, minimal markdown: paragraphs, bullet and numbered lists, **bold**, *italic*, `code`, ### headings */
function renderMd(text) {
  var lines = esc(text || "").split(/\r?\n/), out = [], list = null;
  function inline(s) { return s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/(^|[^*])\*(?!\s)(.+?)\*(?!\*)/g, "$1<em>$2</em>").replace(/`([^`]+)`/g, "<code>$1</code>"); }
  function close() { if (list) { out.push("</" + list + ">"); list = null; } }
  var para = [];
  function flush() { if (para.length) { out.push("<p>" + inline(para.join(" ")) + "</p>"); para = []; } }
  lines.forEach(function (raw) {
    var l = raw.trim(), m;
    if (!l) { flush(); close(); return; }
    if ((m = l.match(/^#{1,4}\s+(.*)$/))) { flush(); close(); out.push("<h4>" + inline(m[1]) + "</h4>"); return; }
    if ((m = l.match(/^[-*•]\s+(.*)$/))) { flush(); if (list !== "ul") { close(); out.push("<ul>"); list = "ul"; } out.push("<li>" + inline(m[1]) + "</li>"); return; }
    if ((m = l.match(/^\d+[.)]\s+(.*)$/))) { flush(); if (list !== "ol") { close(); out.push("<ol>"); list = "ol"; } out.push("<li>" + inline(m[1]) + "</li>"); return; }
    close(); para.push(l);
  });
  flush(); close();
  return out.join("");
}

/* ---------- state ---------- */
var chats = [];
try { chats = JSON.parse(localStorage.getItem(STORE)) || []; } catch (e) { chats = []; }
chats = chats.filter(function (c) { return c && c.id && Array.isArray(c.messages); });
var currentId = null, busy = false, controller = null, thinkTimer = null;
/* Restricted answers are never written to browser storage. */
var REDACTED = "Restricted answer hidden. Sign in and ask again to view it.";
function redact(m) { return { role: m.role, text: REDACTED, restricted: true, redacted: true, at: m.at }; }
function save() {
  try {
    localStorage.setItem(STORE, JSON.stringify(chats.map(function (c) {
      return { id: c.id, title: c.title, createdAt: c.createdAt, updatedAt: c.updatedAt,
        messages: c.messages.filter(function (m) { return m.kind !== "auth"; }).map(function (m) { return m.restricted && !m.redacted ? redact(m) : m; }) };
    })));
  } catch (e) {}
}

/* ---------- access (sign-in for restricted intelligence) ---------- */
var AUTH_KEY = "sisiwenyewe_auth", IDLE_MS = 30 * 60 * 1000, auth = null, lastActive = Date.now();
try { auth = JSON.parse(sessionStorage.getItem(AUTH_KEY)); } catch (e) { auth = null; }
if (!auth || !auth.token || !auth.exp || auth.exp < Date.now()) auth = null;
function storeAuth() { try { if (auth) sessionStorage.setItem(AUTH_KEY, JSON.stringify(auth)); else sessionStorage.removeItem(AUTH_KEY); } catch (e) {} }
function headers() { var h = { "Content-Type": "application/json" }; if (auth) h.Authorization = "Bearer " + auth.token; return h; }
function whoName(u) { if (!u) return ""; var n = (u.name || "").split(/\s+/); return (u.rank ? u.rank + " " : "") + (n.length > 1 ? n[0].charAt(0) + ". " + n.slice(1).join(" ") : (u.name || u.service_no)); }
function signedIn(data) {
  auth = { token: data.token, user: data.user, exp: Date.now() + (data.expires_in || 28800) * 1000 }; lastActive = Date.now();
  storeAuth(); renderAccess(); toast("Signed in as " + whoName(data.user) + ".");
}
function hideRestricted() {
  chats.forEach(function (c) { c.messages.forEach(function (m, i) { if (m.restricted && !m.redacted) c.messages[i] = redact(m); }); });
}
function signOut(reason) {
  if (auth) { try { fetch(API + "/auth/logout", { method: "POST", headers: headers() }); } catch (e) {} }
  auth = null; storeAuth(); hideRestricted(); save(); renderAccess(); renderThread();
  toast(reason || "Signed out. Restricted answers are hidden.");
}
function apiPost(path, body, tok) {
  var h = { "Content-Type": "application/json" }; if (tok) h.Authorization = "Bearer " + tok;
  return fetch(API + path, { method: "POST", headers: h, body: JSON.stringify(body || {}) })
    .then(function (r) { return r.json().catch(function () { return {}; }).then(function (d) { d._status = r.status; return d; }); });
}
function authForm(onDone) {
  var f = el("form", "lock-form"); f.noValidate = true;
  var err = el("p", "lock-err"); err.setAttribute("role", "alert");
  function field(label, type, name, ac, mode) {
    var w = el("label", "lock-field"); w.appendChild(el("span", null, label));
    var i = el("input"); i.type = type; i.name = name; i.autocomplete = ac; i.required = true; i.spellcheck = false; if (mode) i.inputMode = mode; w.appendChild(i); return { w: w, i: i };
  }
  var sn = field("Service number", "text", "username", "username"), pin = field("PIN", "password", "password", "current-password", "numeric");
  sn.i.placeholder = "e.g. RO/12345"; sn.i.autocapitalize = "characters";
  var btn = el("button", "lock-btn", "Sign in"); btn.type = "submit";
  var row = el("div", "lock-row"); row.appendChild(sn.w); row.appendChild(pin.w); f.appendChild(row); f.appendChild(btn); f.appendChild(err);
  var stage = "login", pcToken = null, pinNew, pinConfirm;
  function busyBtn(v, label) { btn.disabled = v; btn.textContent = v ? "Checking…" : label; }
  f.addEventListener("submit", function (e) {
    e.preventDefault(); err.textContent = "";
    if (stage === "login") {
      if (!sn.i.value.trim() || !pin.i.value.trim()) { err.textContent = "Enter your service number and PIN."; return; }
      busyBtn(true, "Sign in");
      apiPost("/auth/login", { service_no: sn.i.value, pin: pin.i.value }).then(function (d) {
        busyBtn(false, "Sign in"); pin.i.value = "";
        if (!d.ok) { err.textContent = d.error || "Sign-in failed. Try again."; pin.i.focus(); return; }
        if (d.must_change_pin) {
          stage = "change"; pcToken = d.token; row.innerHTML = "";
          f.insertBefore(el("p", "lock-note", "Welcome, " + whoName(d.user) + ". This was a one-time PIN. Set your own 6–12 digit PIN to continue."), row);
          pinNew = field("New PIN", "password", "new-password", "new-password", "numeric"); pinConfirm = field("Confirm new PIN", "password", "confirm-password", "new-password", "numeric");
          row.appendChild(pinNew.w); row.appendChild(pinConfirm.w); btn.textContent = "Set PIN and continue"; pinNew.i.focus(); return;
        }
        signedIn(d); onDone();
      }).catch(function () { busyBtn(false, "Sign in"); err.textContent = "Cannot reach the server. Check your connection."; });
    } else {
      if (pinNew.i.value !== pinConfirm.i.value) { err.textContent = "The two PINs do not match."; return; }
      busyBtn(true, "Set PIN and continue");
      apiPost("/auth/change-pin", { new_pin: pinNew.i.value }, pcToken).then(function (d) {
        busyBtn(false, "Set PIN and continue");
        if (!d.ok) { err.textContent = d.error || "Could not set the PIN."; if (d._status === 401) { stage = "login"; } return; }
        pinNew.i.value = pinConfirm.i.value = ""; signedIn(d); onDone();
      }).catch(function () { busyBtn(false, "Set PIN and continue"); err.textContent = "Cannot reach the server. Check your connection."; });
    }
  });
  setTimeout(function () { if (document.activeElement === document.body || document.activeElement === q) sn.i.focus(); }, 60);
  return f;
}
function lockCard(text, onDone) {
  var card = el("div", "lock-card"), h = el("div", "lock-h"); h.appendChild(svg(IC.lock, 16)); h.appendChild(el("b", null, "Restricted information"));
  card.appendChild(h); card.appendChild(el("p", "lock-msg", text || "This information is restricted to authorised Sisiwenyewe personnel."));
  card.appendChild(authForm(onDone));
  card.appendChild(el("small", "lock-foot", "Authorised personnel only. Every access is logged. Never share your PIN."));
  return card;
}
function openSignIn() {
  var m = $("#authModal"), box = $("#authBox"); box.innerHTML = "";
  var x = el("button", "icon-btn lock-x"); x.type = "button"; x.setAttribute("aria-label", "Close"); x.innerHTML = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>';
  x.addEventListener("click", closeSignIn); box.appendChild(x);
  box.appendChild(lockCard("Sign in with your service number and PIN to access restricted intelligence and the live sensor network.", closeSignIn));
  m.hidden = false; closeSide();
}
function closeSignIn() { $("#authModal").hidden = true; }
function renderAccess() {
  var a = $("#access"); if (!a) return; a.innerHTML = "";
  var ic = el("span", "acc-ic"); ic.appendChild(svg(auth ? IC.shield : IC.lock, 15)); a.appendChild(ic);
  var t = el("span", "acc-t");
  t.appendChild(el("b", null, auth ? "AUTHORISED" : "PUBLIC ACCESS"));
  t.appendChild(el("small", null, auth ? whoName(auth.user) : "Restricted items need sign-in"));
  a.appendChild(t);
  var b = el("button", "acc-btn", auth ? "Sign out" : "Sign in"); b.type = "button";
  b.addEventListener("click", function () { if (auth) signOut(); else openSignIn(); });
  a.appendChild(b); a.classList.toggle("on", !!auth);
  var w = thread && thread.querySelector(".welcome"); if (w) renderThread();
}
["click", "keydown", "touchstart"].forEach(function (ev) { document.addEventListener(ev, function () { lastActive = Date.now(); }, { passive: true }); });
setInterval(function () {
  if (!auth) return;
  if (auth.exp < Date.now()) signOut("Your session has ended. Sign in again for restricted information.");
  else if (Date.now() - lastActive > IDLE_MS) signOut("Signed out after 30 minutes of inactivity.");
}, 30000);
function current() { return chats.filter(function (c) { return c.id === currentId; })[0]; }
function newChat(focus) {
  var existing = chats.filter(function (c) { return !c.messages.length; })[0];
  if (existing) { currentId = existing.id; }
  else { var c = { id: "chat_" + Date.now() + "_" + Math.floor(Math.random() * 1e4), title: "New Chat", messages: [], createdAt: new Date().toISOString() }; chats.unshift(c); currentId = c.id; save(); }
  renderHistory(); renderThread(); closeSide();
  if (focus !== false) setTimeout(function () { q.focus(); }, 30);
}

/* ---------- sidebar ---------- */
function groupOf(iso) {
  var d = new Date(iso || Date.now()), now = new Date(), day = 864e5;
  var start = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  if (d.getTime() >= start) return "TODAY";
  if (d.getTime() >= start - day) return "YESTERDAY";
  if (d.getTime() >= start - 7 * day) return "PREVIOUS 7 DAYS";
  return "EARLIER";
}
function renderHistory() {
  historyEl.innerHTML = "";
  var term = searchEl.value.trim().toLowerCase();
  var list = chats.filter(function (c) {
    if (!c.messages.length && c.id !== currentId) return false;
    if (!term) return true;
    return (c.title || "").toLowerCase().indexOf(term) >= 0 || c.messages.some(function (m) { return (m.text || "").toLowerCase().indexOf(term) >= 0; });
  });
  if (!list.length) { historyEl.appendChild(el("div", "empty-h", term ? "No conversations match." : "No conversations yet.")); return; }
  var last = null;
  list.forEach(function (c) {
    var g = groupOf(c.updatedAt || c.createdAt);
    if (g !== last) { historyEl.appendChild(el("div", "grp", g)); last = g; }
    var item = el("div", "h-item" + (c.id === currentId ? " on" : ""));
    var t = el("button", "t", c.messages.length ? c.title : "New conversation"); t.type = "button"; t.title = c.title;
    t.addEventListener("click", function () { currentId = c.id; renderHistory(); renderThread(); closeSide(); });
    var del = el("button", "del"); del.type = "button"; del.setAttribute("aria-label", "Delete conversation"); del.appendChild(svg(IC.trash, 14));
    del.addEventListener("click", function (e) { e.stopPropagation(); removeChat(c.id); });
    item.appendChild(t); item.appendChild(del); historyEl.appendChild(item);
  });
}
function removeChat(id) {
  var idx = chats.findIndex(function (c) { return c.id === id; }), removed = chats[idx];
  chats.splice(idx, 1); save();
  if (currentId === id) { currentId = null; if (chats.length) currentId = chats[0].id; }
  if (!currentId) newChat(false); else { renderHistory(); renderThread(); }
  toast("Conversation deleted.");
  void removed;
}
searchEl.addEventListener("input", renderHistory);

/* ---------- welcome ---------- */
var DOMAINS = [
  { k: "C", name: "Chemical", sub: "Nerve, blister and toxic industrial agents", c: "var(--chem)", qs: ["What are the signs of nerve agent exposure?", "How should responders handle a chlorine release?"] },
  { k: "B", name: "Biological", sub: "Pathogens, toxins and outbreaks", c: "var(--bio)", qs: ["What is anthrax?", "Summarise biological agents"] },
  { k: "R", name: "Radiological", sub: "Sources, dispersal and dose", c: "var(--rad)", qs: ["What is a radiological dispersal device?", "What dose rate is considered dangerous?"] },
  { k: "N", name: "Nuclear", sub: "Detonation effects and protection", c: "var(--nuc)", qs: ["How do people shelter after a nuclear detonation?", "What is radioactive fallout?"] }
];
var SENSOR = [
  { ic: IC.sensor, t: "Live sensor data", d: "Current readings from the radiation network", q: "Show me the latest sensor data and current readings" },
  { ic: IC.wave, t: "AI sensor analysis", d: "Risk level, trend and anomaly detection", q: "Give me a detailed analysis of the current sensor readings including risk level, trend, and anomaly detection" },
  { ic: IC.brief, t: "Threat briefing", d: "A concise briefing from the latest data", q: "Generate a threat briefing based on the latest sensor data" }
];
function radarSvg() {
  var s = '<svg viewBox="0 0 200 200" aria-hidden="true"><defs><radialGradient id="rg" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#F5C518" stop-opacity=".10"/><stop offset="1" stop-color="#F5C518" stop-opacity="0"/></radialGradient>' +
    '<linearGradient id="sw" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#F5C518" stop-opacity="0"/><stop offset="1" stop-color="#F5C518" stop-opacity=".45"/></linearGradient></defs>' +
    '<circle cx="100" cy="100" r="96" fill="url(#rg)" stroke="#253140"/>' +
    [72, 48, 24].map(function (r) { return '<circle cx="100" cy="100" r="' + r + '" fill="none" stroke="#1C2631"/>'; }).join("") +
    '<path d="M100 4V196M4 100H196" stroke="#1C2631"/>' +
    '<g class="sweep"><path d="M100 100 L196 100 A96 96 0 0 0 167.9 32.1 Z" fill="url(#sw)"/><path d="M100 100 L196 100" stroke="#F5C518" stroke-width="1.5"/></g>';
  var pts = [[150, 62, "#FFA552", "0s"], [58, 70, "#6FE0A0", "1.2s"], [70, 146, "#F5C518", "2.4s"], [140, 140, "#FF6B5B", "3.6s"]];
  pts.forEach(function (p) { s += '<circle class="blip" cx="' + p[0] + '" cy="' + p[1] + '" r="4" fill="' + p[2] + '" style="animation-delay:' + p[3] + '"/>'; });
  s += '<text x="12" y="20" fill="#FFA552" font-family="Archivo,Arial,sans-serif" font-weight="800" font-size="14">C</text><text x="178" y="20" fill="#6FE0A0" font-family="Archivo,Arial,sans-serif" font-weight="800" font-size="14">B</text><text x="12" y="192" fill="#F5C518" font-family="Archivo,Arial,sans-serif" font-weight="800" font-size="14">R</text><text x="177" y="192" fill="#FF6B5B" font-family="Archivo,Arial,sans-serif" font-weight="800" font-size="14">N</text>';
  return s + "</svg>";
}
function welcome() {
  var w = el("div", "welcome");
  var hero = el("div", "hero"), r = el("div", "radar"); r.innerHTML = radarSvg(); hero.appendChild(r);
  var txt = el("div"); var h = el("h2"); h.innerHTML = 'Sovereign intelligence for <span>CBRN threats</span>.'; txt.appendChild(h);
  txt.appendChild(el("p", null, "Ask about chemical, biological, radiological and nuclear agents, response protocols and protection, or check the live sensor network."));
  hero.appendChild(txt); w.appendChild(hero);
  w.appendChild(el("div", "eyebrow", "KNOWLEDGE DOMAINS"));
  var g = el("div", "domains");
  DOMAINS.forEach(function (d, i) {
    var c = el("div", "dom"); c.style.setProperty("--c", d.c); c.style.animationDelay = (i * 60) + "ms";
    var hh = el("div", "dom-h"), ic = el("span", "dom-ic", d.k), tt = el("div"); tt.appendChild(el("b", null, d.name)); tt.appendChild(el("small", null, d.sub));
    hh.appendChild(ic); hh.appendChild(tt); c.appendChild(hh);
    d.qs.forEach(function (qq) { var b = el("button", "q-btn", qq); b.type = "button"; b.addEventListener("click", function () { ask(qq); }); c.appendChild(b); });
    g.appendChild(c);
  });
  w.appendChild(g);
  var e2 = el("div", "eyebrow"); e2.style.marginTop = "22px"; e2.textContent = "LIVE SENSOR INTELLIGENCE"; if (!auth) { var lk = el("span", "eb-lock"); lk.appendChild(svg(IC.lock, 11)); lk.appendChild(document.createTextNode("SIGN-IN REQUIRED")); e2.appendChild(lk); } w.appendChild(e2);
  var s = el("div", "sensors");
  SENSOR.forEach(function (x, i) {
    var b = el("button", "sens"); b.type = "button"; b.style.animationDelay = (240 + i * 60) + "ms";
    var ic = el("span", "s-ic"); ic.appendChild(svg(x.ic, 18)); b.appendChild(ic);
    var t = el("span"), bb = el("b", null, x.t), lv = el("span", "live"); lv.appendChild(el("i")); lv.appendChild(document.createTextNode("LIVE")); bb.appendChild(lv);
    t.appendChild(bb); t.appendChild(el("small", null, x.d)); b.appendChild(t);
    b.addEventListener("click", function () { ask(x.q); }); s.appendChild(b);
  });
  w.appendChild(s);
  return w;
}

/* ---------- messages ---------- */
function prettySource(s) {
  if (s === "live_sensor_data" || s === "live_sensor_analysis") return { t: "Live sensor network", live: true };
  if (s === "internal_profile") return { t: "Sisiwenyewe profile" };
  var n = String(s).split(/[\\/]/).pop().replace(/\.(pdf|txt|docx?|md|json)$/i, "").replace(/[_-]+/g, " ").replace(/\s+/g, " ").trim();
  return { t: n.length > 48 ? n.slice(0, 46) + "…" : n };
}
function riskOf(text) { var t = text || "", m = /\b(high|moderate|low)[\s-]+(?:risk|level)\b/i.exec(t) || /\brisk level\s*(?:is|of|:)?\s*(?:assessed as\s*)?(high|moderate|low)\b/i.exec(t); return m ? m[1].toLowerCase() : null; }
function hostOf(u) { try { return new URL(u).hostname.replace(/^www\./, ""); } catch (e) { return ""; } }

function userMsg(m) { var row = el("div", "msg user"); row.appendChild(el("div", "bubble", m.text)); return row; }
function authMsg(m, idx) {
  var row = el("div", "msg bot"), av = el("div", "av"); av.innerHTML = MARK; row.appendChild(av);
  var body = el("div", "bot-body"), meta = el("div", "bot-meta");
  meta.appendChild(el("b", null, "SISIWENYEWE")); meta.appendChild(el("span", null, timeStr(m.at)));
  var tg = el("span", "tag restricted"); tg.appendChild(svg(IC.lock, 11)); tg.appendChild(document.createTextNode("RESTRICTED")); meta.appendChild(tg);
  body.appendChild(meta);
  if (auth) {
    var card = el("div", "lock-card"), p = el("p", "lock-msg", "You are signed in as " + whoName(auth.user) + ".");
    var go = el("button", "lock-btn", "Show the answer"); go.type = "button"; go.addEventListener("click", function () { retry(idx); });
    card.appendChild(p); card.appendChild(go); body.appendChild(card);
  } else {
    body.appendChild(lockCard(m.text, function () { retry(idx); }));
  }
  row.appendChild(body); return row;
}
function botMsg(m, idx, animate) {
  if (m.kind === "auth") return authMsg(m, idx);
  var row = el("div", "msg bot" + (m.redacted ? " redacted" : "")), av = el("div", "av"); av.innerHTML = MARK; row.appendChild(av);
  var body = el("div", "bot-body"), meta = el("div", "bot-meta");
  meta.appendChild(el("b", null, "SISIWENYEWE")); meta.appendChild(el("span", null, timeStr(m.at)));
  if (m.restricted) { var rt = el("span", "tag restricted"); rt.appendChild(svg(IC.lock, 11)); rt.appendChild(document.createTextNode(m.redacted ? "RESTRICTED · HIDDEN" : "RESTRICTED")); meta.appendChild(rt); }
  if (m.ms) meta.appendChild(el("span", null, (m.ms / 1000).toFixed(1) + "s"));
  var isLive = (m.sources || []).some(function (s) { return /live_sensor/.test(s); });
  if (isLive) { var lt = el("span", "tag live"); lt.appendChild(svg(IC.sensor, 12)); lt.appendChild(document.createTextNode("LIVE SENSOR DATA")); meta.appendChild(lt);
    var rk = riskOf(m.text); if (rk) meta.appendChild(el("span", "tag " + rk, rk.toUpperCase() + " RISK")); }
  body.appendChild(meta);
  var ans = el("div", "answer"); body.appendChild(ans);
  var extras = el("div");
  var srcs = (m.sources || []).filter(Boolean);
  if (srcs.length) {
    var sw = el("div", "srcs"), seen = {};
    srcs.forEach(function (s) { var p = prettySource(s); if (!p.t || seen[p.t]) return; seen[p.t] = 1; var c = el("span", "src"); c.appendChild(svg(p.live ? IC.sensor : IC.doc, 13)); c.appendChild(document.createTextNode(p.t)); sw.appendChild(c); });
    if (sw.children.length) extras.appendChild(sw);
  }
  if (m.resources && m.resources.length) {
    var rs = el("div", "res"); rs.appendChild(el("div", "res-h", "FURTHER READING · AUTHORITATIVE SOURCES"));
    m.resources.forEach(function (r) { if (!r || !/^https?:\/\//i.test(r.url || "")) return; var a = el("a"); a.href = r.url; a.target = "_blank"; a.rel = "noopener"; a.appendChild(svg(IC.doc, 16)); var sp = el("span"); sp.appendChild(document.createTextNode(r.title || r.url)); sp.appendChild(el("small", null, hostOf(r.url))); a.appendChild(sp); a.appendChild(svg(IC.ext, 14)); rs.appendChild(a); });
    extras.appendChild(rs);
  }
  var acts = el("div", "acts");
  function act(icon, label, fn) { var b = el("button", "act"); b.type = "button"; b.appendChild(svg(icon, 14)); b.appendChild(document.createTextNode(label)); b.addEventListener("click", function () { fn(b); }); acts.appendChild(b); return b; }
  if (m.redacted) { if (!auth) act(IC.lock, "Sign in", openSignIn); if (idx != null) act(IC.retry, "Ask again", function () { retry(idx); }); extras.appendChild(acts); body.appendChild(extras); row.appendChild(body); ans.innerHTML = renderMd(m.text); return row; }
  act(IC.copy, "Copy", function (b) { copyText(m.text, b); });
  if ("speechSynthesis" in window) act(IC.speak, "Read aloud", function (b) { readAloud(m.text, b); });
  if (idx != null) act(IC.retry, "Retry", function () { retry(idx); });
  extras.appendChild(acts);
  body.appendChild(extras); row.appendChild(body);

  if (animate && !reduce) {
    extras.style.display = "none"; ans.classList.add("caret");
    var words = m.text.split(/(\s+)/), i = 0, step = Math.max(1, Math.ceil(words.length / 90));
    var timer = setInterval(function () {
      i = document.hidden ? words.length : i + step; ans.innerHTML = renderMd(words.slice(0, i).join(""));
      stick();
      if (i >= words.length) { clearInterval(timer); ans.classList.remove("caret"); ans.innerHTML = renderMd(m.text); extras.style.display = ""; stick(); }
    }, 22);
    ans.addEventListener("click", function () { i = words.length; }, { once: true });
  } else { ans.innerHTML = renderMd(m.text); }
  return row;
}
function stick() { thread.scrollTop = thread.scrollHeight; }
function renderThread() {
  var c = current();
  thread.innerHTML = "";
  $("#chatTitle").textContent = c && c.messages.length ? c.title : "CBRN Intelligence";
  if (!c || !c.messages.length) { thread.appendChild(welcome()); thread.scrollTop = 0; return; }
  c.messages.forEach(function (m, i) { thread.appendChild(m.role === "user" ? userMsg(m) : botMsg(m, i, false)); });
  stick();
}

/* ---------- thinking ---------- */
function thinking(isSensor) {
  var row = el("div", "msg bot"), av = el("div", "av"); av.innerHTML = MARK; row.appendChild(av);
  var box = el("div", "think"), ring = el("div", "think-ring"), t = el("div"), b = el("b"), sm = el("small"), st = el("div", "steps");
  var stages = isSensor ? ["Connecting to the sensor network", "Reading the latest measurements", "Checking risk level and trend", "Writing the answer"]
                        : ["Understanding the question", "Searching the CBRN knowledge base", "Cross-checking sources", "Writing the answer"];
  stages.forEach(function () { st.appendChild(el("i")); });
  t.appendChild(b); t.appendChild(sm); t.appendChild(st); box.appendChild(ring); box.appendChild(t); row.appendChild(box);
  var t0 = Date.now(), k = -1;
  function tick() {
    var s = (Date.now() - t0) / 1000, nk = Math.min(stages.length - 1, Math.floor(s / (isSensor ? 3 : 4.5)));
    if (nk !== k) { k = nk; b.textContent = stages[k] + "…"; [].forEach.call(st.children, function (x, j) { x.classList.toggle("on", j <= k); }); }
    sm.textContent = s.toFixed(0) + "s elapsed" + (s > 25 ? " · complex questions can take up to a minute" : "");
  }
  tick(); thinkTimer = setInterval(tick, 500);
  return row;
}

/* ---------- send ---------- */
function setBusy(v) { busy = v; form.classList.toggle("busy", v); sendBtn.setAttribute("aria-label", v ? "Stop" : "Send"); updateSend(); }
function updateSend() { sendBtn.disabled = !busy && !q.value.trim(); }
function ask(text) { q.value = text; autosize(); send(); }
var SENSOR_RE = /sensor|reading|radiation|dose|threat briefing/i;

function send(retryText) {
  if (busy) return;
  var text = (retryText != null ? retryText : q.value).trim();
  if (!text) return;
  var c = current(); if (!c) { newChat(false); c = current(); }
  if (!c.messages.length) c.title = text.length > 48 ? text.slice(0, 46) + "…" : text;
  if (retryText == null) c.messages.push({ role: "user", text: text, at: new Date().toISOString() });
  c.updatedAt = new Date().toISOString(); save();
  q.value = ""; autosize();
  if (thread.querySelector(".welcome")) thread.innerHTML = "";
  if (retryText == null) { thread.appendChild(userMsg(c.messages[c.messages.length - 1])); }
  $("#chatTitle").textContent = c.title; renderHistory();
  var th = thinking(SENSOR_RE.test(text)); thread.appendChild(th); stick();
  setBusy(true);
  controller = window.AbortController ? new AbortController() : null;
  var t0 = Date.now(), chatRef = c;
  var history = c.messages.filter(function (m) { return m.kind !== "auth" && !m.redacted; }).slice(-6).map(function (m) { return { role: m.role, text: m.text }; });
  fetch(API + "/chat", { method: "POST", headers: headers(), body: JSON.stringify({ question: text, history: history }), signal: controller ? controller.signal : undefined })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data && data.auth_required) {
        if (auth) { auth = null; storeAuth(); hideRestricted(); renderAccess(); }
        finish(chatRef, th, { role: "bot", kind: "auth", text: data.answer, at: new Date().toISOString() });
        return;
      }
      var m = { role: "bot", text: (data && data.answer) || FALLBACK, sources: (data && data.sources) || [], resources: (data && data.resources) || [], restricted: !!(data && data.restricted), at: new Date().toISOString(), ms: Date.now() - t0 };
      finish(chatRef, th, m);
    })
    .catch(function (err) {
      if (err && err.name === "AbortError") { clearInterval(thinkTimer); th.remove(); setBusy(false); toast("Stopped."); return; }
      finish(chatRef, th, { role: "bot", text: FALLBACK, sources: [], resources: [], at: new Date().toISOString(), ms: Date.now() - t0 });
    });
}
function finish(c, th, m) {
  clearInterval(thinkTimer); setBusy(false);
  c.messages.push(m); c.updatedAt = new Date().toISOString(); save();
  if (c.id !== currentId) { renderHistory(); return; }
  var row = botMsg(m, c.messages.length - 1, true); th.replaceWith(row); stick();
  renderHistory();
}
function retry(idx) {
  var c = current(); if (!c || busy) return;
  var prev = null; for (var i = idx - 1; i >= 0; i--) { if (c.messages[i].role === "user") { prev = c.messages[i]; break; } }
  if (!prev) return;
  c.messages.splice(idx, 1); save(); renderThread(); send(prev.text);
}
form.addEventListener("submit", function (e) { e.preventDefault(); if (busy) { if (controller) controller.abort(); } else send(); });
q.addEventListener("keydown", function (e) { if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); if (!busy) send(); } });
function autosize() { q.style.height = "auto"; q.style.height = Math.min(180, q.scrollHeight) + "px"; updateSend(); }
q.addEventListener("input", autosize);
document.addEventListener("keydown", function (e) { if (e.key === "/" && document.activeElement !== q && document.activeElement !== searchEl) { e.preventDefault(); q.focus(); } if (e.key === "Escape") { closeSide(); closeSignIn(); } });

/* ---------- actions ---------- */
function copyText(t, b) {
  var done = function () { b.classList.add("on"); b.lastChild.textContent = "Copied"; setTimeout(function () { b.classList.remove("on"); b.lastChild.textContent = "Copy"; }, 1600); };
  if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(t).then(done, function () { toast("Could not copy."); }); else toast("Copy is not available in this browser.");
}
var speaking = null;
function readAloud(t, b) {
  var ss = window.speechSynthesis;
  if (speaking === b) { ss.cancel(); speaking = null; b.classList.remove("on"); b.lastChild.textContent = "Read aloud"; return; }
  ss.cancel(); if (speaking) { speaking.classList.remove("on"); speaking.lastChild.textContent = "Read aloud"; }
  var u = new SpeechSynthesisUtterance(t.replace(/[*#`]/g, "")); u.lang = "en-GB"; u.rate = 1;
  u.onend = function () { if (speaking === b) { speaking = null; b.classList.remove("on"); b.lastChild.textContent = "Read aloud"; } };
  speaking = b; b.classList.add("on"); b.lastChild.textContent = "Stop reading"; ss.speak(u);
}
$("#exportBtn").addEventListener("click", function () {
  var c = current(); if (!c || !c.messages.length) { toast("Ask a question first, then export the conversation."); return; }
  var p = $("#print"); p.innerHTML = "";
  var hasR = c.messages.some(function (m) { return m.restricted && !m.redacted; });
  if (hasR) p.appendChild(el("div", "pr", "RESTRICTED · AUTHORISED PERSONNEL ONLY · EXPORTED BY " + (auth ? auth.user.service_no + " " + whoName(auth.user) : "").toUpperCase()));
  p.appendChild(el("h1", null, "Sisiwenyewe CBRN Intelligence"));
  p.appendChild(el("div", "pm", "CONVERSATION RECORD · " + (c.title || "").toUpperCase() + " · " + new Date().toLocaleString()));
  c.messages.forEach(function (m) {
    if (m.kind === "auth") return;
    if (m.role === "user") p.appendChild(el("div", "pq", "Q: " + m.text));
    else { p.appendChild(el("div", "pa", m.text)); var s = (m.sources || []).map(function (x) { return prettySource(x).t; }).filter(Boolean); if (s.length) p.appendChild(el("div", "ps", "Sources: " + s.join("; "))); }
  });
  p.appendChild(el("div", "ps", "Advisory intelligence. Verify with the responsible authority before operational decisions."));
  if (hasR) p.appendChild(el("div", "pr", "RESTRICTED · DO NOT DISTRIBUTE"));
  window.print();
});

/* ---------- side drawer ---------- */
function closeSide() { app.classList.remove("open"); }
$("#menuBtn").addEventListener("click", function () { app.classList.add("open"); });
$("#sideClose").addEventListener("click", closeSide);
$("#scrim").addEventListener("click", closeSide);
$("#newChat").addEventListener("click", function () { if (busy && controller) controller.abort(); newChat(); });

/* ---------- system status ---------- */
function ping() {
  var s = $("#sysState"), t0 = Date.now(), ctl = window.AbortController ? new AbortController() : null, to = setTimeout(function () { if (ctl) ctl.abort(); }, 8000);
  fetch(API + "/", { method: "GET", signal: ctl ? ctl.signal : undefined, cache: "no-store" }).then(function (r) {
    clearTimeout(to); s.className = "state " + (r.ok ? "ok" : "bad"); s.innerHTML = "<i></i>" + (r.ok ? "Online · " + (Date.now() - t0) + " ms" : "Unavailable");
  }).catch(function () { clearTimeout(to); s.className = "state bad"; s.innerHTML = "<i></i>Offline"; });
}
ping(); setInterval(ping, 60000);

/* ---------- voice ---------- */
var rec = null, listening = false, finalT = "";
function initRec() {
  var SR = window.SpeechRecognition || window.webkitSpeechRecognition; if (!SR) return null;
  var r = new SR(); r.lang = "en-GB"; r.interimResults = true; r.continuous = true;
  r.onstart = function () { finalT = q.value ? q.value.trim() + " " : ""; listening = true; micBtn.classList.add("on"); toast("Listening… tap the microphone again to stop."); };
  r.onresult = function (ev) { var interim = ""; for (var i = ev.resultIndex; i < ev.results.length; i++) { var p = ev.results[i][0].transcript; if (ev.results[i].isFinal) finalT += p + " "; else interim += p; } q.value = (finalT + interim).trim(); autosize(); };
  r.onerror = function (ev) {
    if (ev.error === "no-speech") return;
    listening = false; micBtn.classList.remove("on");
    toast(ev.error === "not-allowed" ? "Microphone access is blocked. Allow it in your browser settings." : ev.error === "audio-capture" ? "No microphone was found." : "Voice input is unavailable right now. Please type your question.");
  };
  r.onend = function () { if (listening) { try { r.start(); } catch (e) { listening = false; micBtn.classList.remove("on"); } } else micBtn.classList.remove("on"); };
  return r;
}
micBtn.addEventListener("click", function () {
  if (!rec) rec = initRec();
  if (!rec) { toast("Voice input is not supported in this browser. Try Chrome or Edge."); return; }
  if (listening) { listening = false; rec.stop(); micBtn.classList.remove("on"); q.focus(); }
  else { try { rec.start(); } catch (e) {} }
});

/* ---------- boot ---------- */
$("#authModal").addEventListener("click", function (e) { if (e.target.id === "authModal") closeSignIn(); });
renderAccess();
if (window.matchMedia && matchMedia('(max-width: 860px)').matches) q.placeholder = 'Ask Sisiwenyewe anything…';
if (!chats.length || !chats[0].messages.length) newChat(false);
else { currentId = chats[0].id; renderHistory(); renderThread(); }
var startEmpty = current(); if (startEmpty && startEmpty.messages.length) newChat(false);
updateSend();
})();
