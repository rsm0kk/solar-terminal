# -*- coding: utf-8 -*-
"""SOLAR ANALYST TERMINAL — HTML 템플릿.

`/*__DATA__*/{}` 자리에 dashboard.json 이 통째로 주입된다.
마크업에 숫자를 하드코딩하지 않는다. 외부 CDN·웹폰트·라이브러리를 쓰지 않는다.
"""

HTML = r"""<!doctype html>
<html lang="ko" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<link rel="icon" href="data:,">
<title>SOLAR ANALYST TERMINAL</title>
<style>
/* 밝은 배경 + 진한 글씨가 기본. 본문 대비 12:1 이상으로 잡아 장시간 숫자를 봐도 눈이 편하게. */
:root{
  --bg:#f3f6f9; --panel:#ffffff; --panel-2:#f7f9fc;
  --navy:#172b4d; --navy-2:#223b66;
  --line:#d9e0e8; --line-soft:#e9edf2;
  --ink:#172033; --ink-2:#475467; --ink-3:#667085;
  --up:#087a55; --up-soft:#d8f3e7;
  --down:#b42318; --down-soft:#fee4e2;
  --flat:#667085;
  --accent:#175cd3; --accent-soft:#eaf2ff;
  --warn:#8b4e00; --warn-soft:#fff0cc;
  --shadow:0 10px 26px rgba(23,43,77,.07);
  --radius:12px;
  --mono:"Consolas","D2Coding","Menlo",monospace;
}
html[data-theme="dark"]{
  --bg:#0d1420; --panel:#16202f; --panel-2:#1b2739;
  --navy:#0b1526; --navy-2:#16233b;
  --line:#243348; --line-soft:#1e2b3d;
  --ink:#eaf1fa; --ink-2:#b3c3d6; --ink-3:#8296ad;
  --up:#3ad6b5; --up-soft:rgba(58,214,181,.16);
  --down:#ff8a63; --down-soft:rgba(255,138,99,.16);
  --flat:#8296ad;
  --accent:#69b0ff; --accent-soft:rgba(105,176,255,.16);
  --warn:#f0bd5c; --warn-soft:rgba(240,189,92,.16);
  --shadow:0 10px 26px rgba(0,0,0,.35);
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Malgun Gothic","Apple SD Gothic Neo",Arial,sans-serif;
  font-size:13px;line-height:1.45;-webkit-font-smoothing:antialiased}
button,input,select{font:inherit;color:inherit}
button{cursor:pointer;background:none;border:none}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
.num{font-variant-numeric:tabular-nums;font-family:var(--mono)}

/* ---------- 상단 고정 ---------- */
/* 네이비 헤더 + 흰 글씨, 그 아래 밝은 탭바. 헤더 대비 13:1. */
.topbar{position:sticky;top:0;z-index:50;box-shadow:0 6px 18px rgba(23,43,77,.08)}
.topbar-main{display:flex;align-items:center;gap:14px;flex-wrap:wrap;padding:10px 16px;
  background:linear-gradient(100deg,rgba(255,255,255,.07),transparent 46%),var(--navy);
  color:#fff}
.topbar-main .grow{flex:1 1 auto}
.brand{font-size:15px;font-weight:800;letter-spacing:.14em;white-space:nowrap;color:#fff}
.brand em{font-style:normal;color:#8fc0ff}
.meta-chips{display:flex;gap:7px;flex-wrap:wrap;align-items:center}
.mchip{display:inline-flex;align-items:center;gap:5px;padding:3px 9px;border-radius:999px;
  background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.22);
  font-size:11.5px;color:#d3e2f7;white-space:nowrap}
.mchip b{color:#fff;font-weight:700}
.mchip.ok{background:rgba(46,196,166,.24);border-color:rgba(46,196,166,.5);color:#c9f6e8}
.mchip.bad{background:rgba(255,138,99,.24);border-color:rgba(255,138,99,.55);color:#ffd9cd}
.mchip.warn{background:rgba(240,189,92,.24);border-color:rgba(240,189,92,.55);color:#ffeec4}
.grow{flex:1 1 auto}
.tools{display:flex;gap:6px;align-items:center;flex-wrap:wrap}
.tool{padding:5px 10px;border:1px solid rgba(255,255,255,.28);border-radius:7px;
  background:rgba(255,255,255,.1);font-size:11.5px;font-weight:700;color:#fff;white-space:nowrap}
.tool:hover{background:rgba(255,255,255,.2);border-color:#fff}
#search{padding:5px 10px;border:1px solid rgba(255,255,255,.28);border-radius:7px;
  background:rgba(255,255,255,.12);color:#fff;min-width:180px;font-size:12px}
#search::placeholder{color:rgba(255,255,255,.6)}
#search:focus{outline:2px solid #8fc0ff;outline-offset:-1px;background:rgba(255,255,255,.2)}

.tabs{display:flex;gap:2px;overflow-x:auto;padding:0 16px;background:var(--panel);
  border-bottom:1px solid var(--line);scrollbar-width:thin}
.tab{padding:9px 14px;border-bottom:2px solid transparent;font-size:12.5px;font-weight:700;
  color:var(--ink-3);white-space:nowrap}
.tab:hover{color:var(--ink);background:var(--panel-2)}
.tab[aria-selected="true"]{color:var(--accent);border-bottom-color:var(--accent);
  background:var(--accent-soft)}
.tab .cnt{font-size:10px;color:var(--ink-3);margin-left:4px}

/* ---------- 레이아웃 ---------- */
.shell{max-width:1680px;margin:0 auto;padding:14px 16px 60px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);
  padding:12px 14px 14px;margin-bottom:12px;box-shadow:var(--shadow)}
.panel-head{display:flex;align-items:baseline;justify-content:space-between;gap:10px;
  margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid var(--line-soft);flex-wrap:wrap}
.panel-title{margin:0;font-size:13.5px;font-weight:800;letter-spacing:-.01em}
.panel-sub{font-size:11px;color:var(--ink-3)}
.grid{display:grid;gap:12px}
.g2{grid-template-columns:repeat(2,minmax(0,1fr))}
.g3{grid-template-columns:repeat(3,minmax(0,1fr))}
.g4{grid-template-columns:repeat(4,minmax(0,1fr))}
@media(max-width:1180px){.g3,.g4{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:760px){.g2,.g3,.g4{grid-template-columns:1fr}
  .topbar-main{padding:8px 10px}.shell{padding:10px}}

/* ---------- 카드 ---------- */
.stat{background:var(--panel-2);border:1px solid var(--line-soft);border-radius:8px;padding:10px 12px}
.stat-label{font-size:11px;color:var(--ink-3);font-weight:700}
.stat-val{margin-top:5px;font-size:21px;font-weight:800;letter-spacing:-.02em}
.stat-val .u{font-size:11px;color:var(--ink-3);margin-left:3px;font-weight:700}
.stat-sub{margin-top:4px;font-size:11px;color:var(--ink-3);display:flex;gap:6px;flex-wrap:wrap;align-items:center}
.up{color:var(--up)} .down{color:var(--down)} .flat{color:var(--flat)}

.badge{display:inline-flex;align-items:center;gap:3px;padding:1px 6px;border-radius:4px;
  font-size:10px;font-weight:800;letter-spacing:.02em;white-space:nowrap;
  background:var(--panel-2);border:1px solid var(--line);color:var(--ink-2)}
.badge.t1,.badge.t2{border-color:var(--up);color:var(--up);background:var(--up-soft)}
.badge.t3{border-color:var(--accent);color:var(--accent);background:var(--accent-soft)}
.badge.t4{border-color:var(--line);color:var(--ink-2)}
.badge.t6,.badge.est{border-color:var(--warn);color:var(--warn);background:var(--warn-soft)}
.badge.bad{border-color:var(--down);color:var(--down);background:var(--down-soft)}
.badge.good{border-color:var(--up);color:var(--up);background:var(--up-soft)}

/* ---------- 표 ---------- */
.tbl-wrap{overflow-x:auto;max-height:520px;overflow-y:auto}
table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}
thead th{position:sticky;top:0;z-index:2;background:var(--panel-2);padding:7px 9px;
  border-bottom:1px solid var(--line);font-size:11px;font-weight:800;color:var(--ink-3);
  text-align:right;white-space:nowrap;cursor:pointer;user-select:none}
thead th:hover{color:var(--ink)}
thead th:first-child,tbody td:first-child{text-align:left}
thead th.l,tbody td.l{text-align:left}
tbody td{padding:6px 9px;border-bottom:1px solid var(--line-soft);text-align:right;
  white-space:nowrap;font-size:12px}
tbody tr:hover{background:var(--panel-2)}
tbody td.name{font-weight:700;color:var(--ink)}
tbody td.wrap{white-space:normal;text-align:left;max-width:460px}
.muted{color:var(--ink-3)}
.empty{padding:22px 14px;text-align:center;color:var(--ink-3);font-size:12px;
  background:var(--panel-2);border:1px dashed var(--line);border-radius:8px}
.empty b{color:var(--ink-2);display:block;margin-bottom:5px;font-size:12.5px}
.empty code{background:var(--bg);padding:1px 5px;border-radius:3px;font-family:var(--mono);font-size:11px}

/* ---------- 차트 ---------- */
.chart-head{display:flex;justify-content:space-between;align-items:center;gap:8px;
  margin-bottom:6px;flex-wrap:wrap}
.chart-title{font-size:12.5px;font-weight:700}
.ranges{display:flex;gap:3px}
.range{padding:2px 7px;border:1px solid var(--line);border-radius:5px;font-size:10.5px;
  font-weight:700;color:var(--ink-3)}
.range[aria-pressed="true"]{background:var(--accent-soft);border-color:var(--accent);color:var(--accent)}
.legend{display:flex;gap:9px;flex-wrap:wrap;margin-top:6px}
.lg{display:inline-flex;align-items:center;gap:5px;font-size:11px;color:var(--ink-2);cursor:pointer}
.lg .sw{width:9px;height:9px;border-radius:2px}
.lg.off{opacity:.35;text-decoration:line-through}
svg.chart{width:100%;display:block;overflow:visible}
.ax{stroke:var(--line-soft);stroke-width:1}
.axt{fill:var(--ink-3);font-size:10px;font-family:var(--mono)}
.gl{stroke:var(--line-soft);stroke-width:1;stroke-dasharray:2 3;opacity:.55}
/* 그래프 위에 마우스를 올리면 그 지점의 정확한 값이 뜬다.
   차트만 덩그러니 있으면 값을 읽을 수 없으므로 툴팁은 선택이 아니라 필수. */
.tip{position:fixed;z-index:200;pointer-events:none;background:var(--panel);
  border:1px solid var(--ink-3);border-radius:8px;padding:8px 10px;font-size:12px;
  color:var(--ink);box-shadow:0 10px 28px rgba(23,43,77,.22);max-width:320px;display:none}
.tip .tt{font-weight:800;margin-bottom:5px;font-size:12px;color:var(--ink);
  padding-bottom:4px;border-bottom:1px solid var(--line)}
.tip .tr{display:flex;justify-content:space-between;gap:14px;margin-top:3px;align-items:baseline}
.tip .tr b{font-family:var(--mono);font-weight:800;white-space:nowrap}
.tip .ts{color:var(--ink-3);font-size:10.5px;margin-top:6px;padding-top:5px;
  border-top:1px solid var(--line-soft);line-height:1.4}
.chart-hint{font-size:10.5px;color:var(--ink-3);margin-top:3px}
svg.chart{cursor:crosshair}

/* ---------- 히트맵 ---------- */
.heat{display:grid;gap:2px;margin-top:6px}
.heat-cell{padding:5px 4px;border-radius:3px;font-size:10px;text-align:center;font-weight:700}
.heat-lbl{font-size:10px;color:var(--ink-3);padding:5px 3px;text-align:right;white-space:nowrap}

/* ---------- 브리핑 ---------- */
.brief-head{background:var(--panel-2);border-left:3px solid var(--accent);
  border-radius:0 8px 8px 0;padding:11px 14px;margin-bottom:10px}
.brief-head li{margin:4px 0}
.brief-sec{margin-bottom:12px}
.brief-sec h4{margin:0 0 6px;font-size:12px;color:var(--ink-2);font-weight:800;
  letter-spacing:.03em;text-transform:uppercase}
.brief-list{margin:0;padding-left:16px}
.brief-list li{margin:3px 0;font-size:12px;color:var(--ink-2)}
.brief-list li.nodata{color:var(--ink-3);font-style:italic}
ul.clean{list-style:none;margin:0;padding:0}

/* ---------- 시그널 ---------- */
.sig-card{background:var(--panel-2);border:1px solid var(--line-soft);border-radius:8px;padding:11px 12px}
.sig-top{display:flex;justify-content:space-between;align-items:flex-start;gap:8px}
.sig-name{font-size:13px;font-weight:800}
.sig-model{font-size:10.5px;color:var(--ink-3);margin-top:2px}
.sig-score{font-size:22px;font-weight:800;text-align:right;line-height:1.1}
.sig-delta{font-size:10.5px;font-weight:700}
.sig-bar{height:5px;border-radius:3px;background:var(--line);margin:9px 0 7px;position:relative;overflow:hidden}
.sig-bar i{position:absolute;top:0;bottom:0;display:block;border-radius:3px}
.sig-drv{font-size:11px;color:var(--ink-2);margin:2px 0;display:flex;justify-content:space-between;gap:8px}
.sig-drv .v{font-family:var(--mono);white-space:nowrap}

/* ---------- 상태 ---------- */
.st-card{background:var(--panel-2);border:1px solid var(--line-soft);border-radius:8px;
  padding:10px 12px;border-left:3px solid var(--flat)}
.st-card.ok{border-left-color:var(--up)}
.st-card.stale{border-left-color:var(--warn)}
.st-card.error{border-left-color:var(--down)}
.st-card.no_key{border-left-color:var(--accent)}
.st-card.manual_empty{border-left-color:var(--ink-3)}
.st-name{font-size:12.5px;font-weight:800;display:flex;justify-content:space-between;gap:8px;align-items:center}
.st-row{display:flex;justify-content:space-between;gap:10px;font-size:11px;color:var(--ink-3);margin-top:3px}
.st-row b{color:var(--ink-2);font-weight:600}
.st-msg{margin-top:6px;font-size:11px;color:var(--ink-2);background:var(--bg);
  padding:5px 7px;border-radius:5px;word-break:break-word}
.hidden{display:none!important}
.disclaimer{font-size:11px;color:var(--ink-3);margin-top:10px;padding:8px 11px;
  background:var(--panel-2);border-radius:6px;border:1px solid var(--line-soft)}
</style>
</head>
<body>
<div class="topbar">
  <div class="topbar-main">
    <div class="brand">SOLAR <em>ANALYST</em> TERMINAL</div>
    <div class="meta-chips" id="metaChips"></div>
    <span class="grow"></span>
    <div class="tools">
      <input id="search" type="search" placeholder="지표·기업·출처 검색" autocomplete="off">
      <button class="tool" id="btnTheme">다크</button>
      <button class="tool" id="btnCsv">CSV</button>
    </div>
  </div>
  <div class="tabs" id="tabs"></div>
</div>

<div class="shell" id="shell"></div>
<div class="tip" id="tip"></div>

<script>
const DATA = /*__DATA__*/{};

/* ============================ 유틸 ============================ */
const $ = (s, r) => (r || document).querySelector(s);
const el = (tag, cls, html) => { const n = document.createElement(tag);
  if (cls) n.className = cls; if (html != null) n.innerHTML = html; return n; };
const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g,
  c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function fmt(v, digits) {
  if (v == null || isNaN(v)) return "-";
  const a = Math.abs(v);
  if (digits != null) return v.toLocaleString("ko-KR", { minimumFractionDigits: digits, maximumFractionDigits: digits });
  if (a >= 10000) return v.toLocaleString("ko-KR", { maximumFractionDigits: 0 });
  if (a >= 100) return v.toLocaleString("ko-KR", { maximumFractionDigits: 1 });
  if (a >= 1) return v.toLocaleString("ko-KR", { maximumFractionDigits: 2 });
  return v.toLocaleString("ko-KR", { maximumFractionDigits: 4 });
}
function pct(v) { return v == null || isNaN(v) ? "-" : (v >= 0 ? "+" : "") + v.toFixed(1) + "%"; }
function cls(v) { return v == null || isNaN(v) ? "flat" : v > 0.02 ? "up" : v < -0.02 ? "down" : "flat"; }

/* period → Date (YYYY / YYYY-MM / YYYY-MM-DD / YYYYQn) */
function pdate(p) {
  p = String(p);
  if (/^\d{4}Q[1-4]$/.test(p)) return new Date(+p.slice(0, 4), (+p[5]) * 3 - 1, 28);
  if (/^\d{4}-\d{2}-\d{2}$/.test(p)) return new Date(p + "T00:00:00");
  if (/^\d{4}-\d{2}$/.test(p)) return new Date(+p.slice(0, 4), +p.slice(5, 7) - 1, 28);
  if (/^\d{4}$/.test(p)) return new Date(+p, 11, 31);
  return new Date(p);
}
const S = (m, e) => DATA.series[m + "|" + (e || "GLOBAL")] || null;
function seriesFor(metric) {
  return Object.keys(DATA.series).filter(k => k.split("|")[0] === metric).map(k => DATA.series[k]);
}
const COMPANIES = DATA.companies || [];
const CNAME = {}; COMPANIES.forEach(c => CNAME[c.id] = c.name);
const PALETTE = ["#4a9eff", "#2ec4a6", "#f2683c", "#e0a63c", "#a78bfa", "#f472b6", "#60d394", "#94a3b8"];

function tierBadge(t, isManual, isEst) {
  const lbl = (DATA.meta.tier_labels || {})[String(t)] || ("tier" + t);
  let out = `<span class="badge t${t}">${esc(lbl)}</span>`;
  if (isEst) out += ` <span class="badge est">추정</span>`;
  if (isManual) out += ` <span class="badge t6">수기</span>`;
  return out;
}

/* ============================ 차트 ============================ */
const RANGES = [["1M", 30], ["3M", 91], ["6M", 182], ["1Y", 365], ["3Y", 1095], ["전체", 0]];
const tip = $("#tip");

function showTip(html, ev) {
  tip.innerHTML = html; tip.style.display = "block";
  const r = tip.getBoundingClientRect();
  let x = ev.clientX + 14, y = ev.clientY + 14;
  if (x + r.width > innerWidth - 8) x = ev.clientX - r.width - 14;
  if (y + r.height > innerHeight - 8) y = ev.clientY - r.height - 14;
  tip.style.left = Math.max(6, x) + "px"; tip.style.top = Math.max(6, y) + "px";
}
const hideTip = () => tip.style.display = "none";

/**
 * 시계열 차트. 단위가 다른 시리즈는 같은 축에 그리지 않는다 —
 * normalize:true 를 주면 100 기준 정규화해서 비교한다.
 */
function chart(host, series, opts) {
  opts = opts || {};
  series = (series || []).filter(s => s && s.points && s.points.length);
  if (!series.length) {
    host.appendChild(el("div", "empty", `<b>데이터 없음</b>${esc(opts.emptyHint || "수집된 시계열이 없습니다.")}`));
    return;
  }
  // 단위 혼재 방어
  const units = [...new Set(series.map(s => s.unit))];
  const normalize = opts.normalize || (units.length > 1 && !opts.allowMixed);

  const wrap = el("div");
  const head = el("div", "chart-head");
  head.appendChild(el("div", "chart-title", esc(opts.title || "") +
    (normalize ? ' <span class="muted" style="font-weight:400">(100 기준 정규화)</span>'
      : ` <span class="muted" style="font-weight:400">${esc(units[0] || "")}</span>`)));
  const ranges = el("div", "ranges");
  head.appendChild(ranges);
  wrap.appendChild(head);

  const svgBox = el("div");
  wrap.appendChild(svgBox);
  const legend = el("div", "legend");
  wrap.appendChild(legend);
  host.appendChild(wrap);

  const off = new Set();
  let days = opts.defaultDays != null ? opts.defaultDays : 365;

  RANGES.forEach(([lbl, d]) => {
    const b = el("button", "range", lbl);
    b.onclick = () => { days = d; draw(); };
    b.dataset.d = d;
    ranges.appendChild(b);
  });

  function draw() {
    [...ranges.children].forEach(b => b.setAttribute("aria-pressed", String(+b.dataset.d === days)));
    svgBox.innerHTML = ""; legend.innerHTML = "";

    const cutoff = days ? Date.now() - days * 864e5 : -Infinity;
    const vis = series.filter(s => !off.has(s.label + s.entity));
    const prepared = vis.map((s, i) => {
      let pts = s.points.map(p => ({ p: p[0], t: pdate(p[0]).getTime(), v: p[1] }))
        .filter(p => p.t >= cutoff && p.v != null);
      if (pts.length < 2 && s.points.length >= 2) {
        pts = s.points.slice(-2).map(p => ({ p: p[0], t: pdate(p[0]).getTime(), v: p[1] }));
      }
      let base = null;
      if (normalize && pts.length) { base = pts[0].v; }
      return { s, i, pts, base, color: s.color || PALETTE[series.indexOf(s) % PALETTE.length] };
    }).filter(x => x.pts.length);

    if (!prepared.length) {
      svgBox.appendChild(el("div", "empty", "<b>선택 기간에 데이터 없음</b>기간을 넓혀 보세요."));
      return;
    }

    const W = 1000, H = opts.height || 230, m = { t: 12, r: 14, b: 26, l: 54 };
    const iw = W - m.l - m.r, ih = H - m.t - m.b;
    const val = x => p => normalize && x.base ? p.v / x.base * 100 : p.v;

    let tMin = Infinity, tMax = -Infinity, vMin = Infinity, vMax = -Infinity;
    prepared.forEach(x => x.pts.forEach(p => {
      tMin = Math.min(tMin, p.t); tMax = Math.max(tMax, p.t);
      const v = val(x)(p); vMin = Math.min(vMin, v); vMax = Math.max(vMax, v);
    }));
    if (tMax === tMin) { tMin -= 864e5; tMax += 864e5; }
    let pad = (vMax - vMin) * 0.12 || Math.abs(vMax || 1) * 0.12;
    if (opts.zeroBase && vMin > 0) vMin = 0; else vMin -= pad;
    vMax += pad;
    if (vMax === vMin) { vMax += 1; vMin -= 1; }

    const X = t => m.l + (t - tMin) / (tMax - tMin) * iw;
    const Y = v => m.t + ih - (v - vMin) / (vMax - vMin) * ih;

    const ns = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.setAttribute("class", "chart");
    svg.setAttribute("preserveAspectRatio", "none");
    svg.style.height = H + "px";
    const mk = (n, a) => { const e = document.createElementNS(ns, n);
      for (const k in a) e.setAttribute(k, a[k]); return e; };

    // y축 눈금
    for (let i = 0; i <= 4; i++) {
      const v = vMin + (vMax - vMin) * i / 4, y = Y(v);
      svg.appendChild(mk("line", { x1: m.l, x2: W - m.r, y1: y, y2: y, class: "gl" }));
      const tx = mk("text", { x: m.l - 6, y: y + 3, class: "axt", "text-anchor": "end" });
      tx.textContent = fmt(v); svg.appendChild(tx);
    }
    // 0선 강조
    if (vMin < 0 && vMax > 0) {
      svg.appendChild(mk("line", { x1: m.l, x2: W - m.r, y1: Y(0), y2: Y(0), class: "ax" }));
    }
    // x축 눈금
    const NT = Math.min(6, Math.max(2, Math.floor(iw / 150)));
    for (let i = 0; i <= NT; i++) {
      const t = tMin + (tMax - tMin) * i / NT, x = X(t), d = new Date(t);
      const lab = (tMax - tMin) > 5 * 365 * 864e5 ? d.getFullYear()
        : (tMax - tMin) > 200 * 864e5 ? `${String(d.getFullYear()).slice(2)}.${d.getMonth() + 1}`
          : `${d.getMonth() + 1}.${d.getDate()}`;
      const tx = mk("text", { x, y: H - 8, class: "axt", "text-anchor": "middle" });
      tx.textContent = lab; svg.appendChild(tx);
    }
    svg.appendChild(mk("line", { x1: m.l, x2: W - m.r, y1: m.t + ih, y2: m.t + ih, class: "ax" }));

    // 시리즈
    prepared.forEach(x => {
      const f = val(x);
      if (opts.kind === "bar" && prepared.length === 1) {
        const bw = Math.max(1.5, iw / x.pts.length * 0.62);
        x.pts.forEach(p => {
          const y0 = Y(Math.max(0, vMin)), y1 = Y(f(p));
          svg.appendChild(mk("rect", { x: X(p.t) - bw / 2, y: Math.min(y0, y1),
            width: bw, height: Math.abs(y1 - y0) || 1, fill: x.color, opacity: .65 }));
        });
      } else {
        const d = x.pts.map((p, i) => (i ? "L" : "M") + X(p.t).toFixed(1) + " " + Y(f(p)).toFixed(1)).join(" ");
        svg.appendChild(mk("path", { d, fill: "none", stroke: x.color, "stroke-width": 1.9,
          "stroke-linejoin": "round", "stroke-linecap": "round" }));
        const last = x.pts[x.pts.length - 1];
        svg.appendChild(mk("circle", { cx: X(last.t), cy: Y(f(last)), r: 2.6, fill: x.color }));
      }
    });

    // ---- 호버: 커서 위치의 정확한 값을 표시 ----
    // 세로 가이드선 + 각 시리즈의 해당 지점에 마커를 찍고, 툴팁에 값·단위·출처를 낸다.
    const hov = mk("line", { x1: 0, x2: 0, y1: m.t, y2: m.t + ih,
      stroke: "currentColor", "stroke-width": 1, "stroke-dasharray": "3 3", opacity: 0 });
    svg.appendChild(hov);
    const marks = prepared.map(x => {
      const c = mk("circle", { r: 4.2, fill: x.color, stroke: "var(--panel)",
        "stroke-width": 1.6, opacity: 0, "pointer-events": "none" });
      svg.appendChild(c);
      return c;
    });
    const hit = mk("rect", { x: m.l, y: m.t, width: iw, height: ih, fill: "transparent" });
    svg.appendChild(hit);

    function moveTo(ev) {
      const r = svg.getBoundingClientRect();
      if (!r.width) return;
      // 화면 좌표 → viewBox 좌표 → 시간축
      const vx = (ev.clientX - r.left) / r.width * W;
      const ratio = Math.min(1, Math.max(0, (vx - m.l) / iw));
      const t = tMin + ratio * (tMax - tMin);

      hov.setAttribute("x1", X(t)); hov.setAttribute("x2", X(t)); hov.setAttribute("opacity", .45);

      let rows = "", label = "";
      prepared.forEach((x, i) => {
        // 정규화 변환함수는 시리즈마다 다르므로 여기서 다시 만든다
        // (그리기 루프 안의 지역변수를 쓰면 ReferenceError 로 툴팁이 통째로 죽는다)
        const fx = val(x);
        let best = null, bd = Infinity;
        x.pts.forEach(p => { const d = Math.abs(p.t - t); if (d < bd) { bd = d; best = p; } });
        if (!best) { marks[i].setAttribute("opacity", 0); return; }
        label = best.p;
        marks[i].setAttribute("cx", X(best.t));
        marks[i].setAttribute("cy", Y(fx(best)));
        marks[i].setAttribute("opacity", 1);

        const name = esc(x.s.label) + (x.s.entity && x.s.entity !== "GLOBAL"
          ? " · " + esc(CNAME[x.s.entity] || x.s.entity) : "");
        const shown = normalize
          ? `${fx(best).toFixed(1)} <span style="opacity:.65">(원값 ${fmt(best.v)} ${esc(x.s.unit)})</span>`
          : `${fmt(best.v)} <span style="opacity:.7">${esc(x.s.unit)}</span>`;
        rows += `<div class="tr"><span style="color:${x.color}">■ ${name}</span><b>${shown}</b></div>`;
      });

      const src = prepared[0].s;
      const badge = src.is_estimate ? " · 추정" : src.is_manual ? " · 수기입력" : "";
      showTip(`<div class="tt">${esc(label)}</div>${rows}
        <div class="ts">출처 ${esc(src.source)}${badge}<br>기준일 ${esc(src.as_of)} · 발표주기 ${esc(src.freq)}</div>`, ev);
    }
    function leave() {
      hideTip();
      hov.setAttribute("opacity", 0);
      marks.forEach(c => c.setAttribute("opacity", 0));
    }
    hit.addEventListener("mousemove", moveTo);
    hit.addEventListener("mouseleave", leave);
    // 터치 기기에서도 값을 읽을 수 있게
    hit.addEventListener("touchmove", ev => {
      if (ev.touches && ev.touches[0]) { moveTo(ev.touches[0]); ev.preventDefault(); }
    }, { passive: false });
    hit.addEventListener("touchend", leave);

    svgBox.appendChild(svg);
    svgBox.appendChild(el("div", "chart-hint", "그래프 위에 마우스를 올리면 그 시점의 정확한 값이 표시됩니다"));

    // 범례 (클릭으로 토글)
    series.forEach((s, i) => {
      const key = s.label + s.entity;
      const color = PALETTE[i % PALETTE.length];
      const name = (s.entity && s.entity !== "GLOBAL")
        ? (CNAME[s.entity] || s.entity) + (series.length > 1 && units.length === 1 ? "" : " · " + s.label)
        : s.label;
      const g = el("span", "lg" + (off.has(key) ? " off" : ""),
        `<span class="sw" style="background:${color}"></span>${esc(name)}`);
      g.onclick = () => { off.has(key) ? off.delete(key) : off.add(key);
        if (off.size >= series.length) off.delete(key); draw(); };
      legend.appendChild(g);
    });
  }
  draw();
}

/* 스몰멀티플 */
function smallMultiples(host, defs) {
  const grid = el("div", "grid g3");
  let drawn = 0;
  defs.forEach(d => {
    const s = d.series && d.series.length ? d.series : (S(d.metric, d.entity) ? [S(d.metric, d.entity)] : []);
    if (!s.length) return;
    drawn++;
    const cell = el("div", "stat");
    chart(cell, s, { title: d.title, height: 150, defaultDays: d.days || 365, kind: d.kind });
    grid.appendChild(cell);
  });
  if (!drawn) { host.appendChild(emptyManual("공급망 가격")); return; }
  host.appendChild(grid);
}

function emptyManual(what) {
  return el("div", "empty", `<b>${esc(what)} 데이터가 아직 없습니다</b>
    자동 수집이 불가능한 유료·구독 데이터입니다. 우회하지 않고 수기 입력으로 채웁니다.<br>
    <code>data/manual/solar_supply_chain_prices.csv</code> 를 채운 뒤
    <code>python scripts/update_all.py</code> 를 실행하면 이 화면이 자동으로 살아납니다.`);
}

/* KPI 타일 */
function statTile(s, opts) {
  opts = opts || {};
  const box = el("div", "stat");
  if (!s) {
    box.innerHTML = `<div class="stat-label">${esc(opts.label || "")}</div>
      <div class="stat-val muted" style="font-size:15px">데이터 없음</div>
      <div class="stat-sub">${esc(opts.hint || "수집되지 않음")}</div>`;
    return box;
  }
  const ch = s.changes || {};
  const c = ch.last;
  box.innerHTML = `<div class="stat-label">${esc(opts.label || s.label)}</div>
    <div class="stat-val">${fmt(s.latest)}<span class="u">${esc(s.unit)}</span></div>
    <div class="stat-sub">
      <span class="${cls(c)}">${pct(c)}</span>
      <span class="muted">${esc(s.as_of)}</span>
      ${tierBadge(s.tier, s.is_manual, s.is_estimate)}
    </div>`;
  return box;
}

/* 정렬 가능한 표 */
function table(host, cols, rows, opts) {
  opts = opts || {};
  if (!rows.length) {
    host.appendChild(el("div", "empty", `<b>표시할 행이 없습니다</b>${esc(opts.empty || "")}`));
    return;
  }
  const wrap = el("div", "tbl-wrap");
  const t = el("table");
  const thead = el("thead");
  const tr = el("tr");
  cols.forEach((c, i) => {
    const th = el("th", c.l ? "l" : "", esc(c.t));
    th.onclick = () => sort(i);
    tr.appendChild(th);
  });
  thead.appendChild(tr); t.appendChild(thead);
  const tb = el("tbody"); t.appendChild(tb);
  let dir = 1, sortIdx = opts.sortBy != null ? opts.sortBy : -1;

  function render() {
    tb.innerHTML = "";
    rows.forEach(r => {
      const trr = el("tr");
      if (r._search) trr.dataset.search = r._search;
      cols.forEach((c, i) => {
        const cell = c.render ? c.render(r) : { html: esc(r[c.k]), cls: "" };
        const td = el("td", (c.l ? "l " : "") + (cell.cls || ""), cell.html);
        trr.appendChild(td);
      });
      tb.appendChild(trr);
    });
  }
  function sort(i) {
    dir = sortIdx === i ? -dir : -1; sortIdx = i;
    const c = cols[i];
    rows.sort((a, b) => {
      let x = c.sortVal ? c.sortVal(a) : a[c.k], y = c.sortVal ? c.sortVal(b) : b[c.k];
      if (x == null) return 1; if (y == null) return -1;
      if (typeof x === "number" && typeof y === "number") return (x - y) * dir;
      return String(x).localeCompare(String(y), "ko") * dir;
    });
    render();
  }
  if (sortIdx >= 0) sort(sortIdx); else render();
  wrap.appendChild(t); host.appendChild(wrap);
}

/* ============================ 탭 ============================ */
const TABS = [
  ["today", "오늘의 결론", tabToday],
  ["supply", "공급망 가격", tabSupply],
  ["global", "글로벌 수요", tabGlobal],
  ["korea", "국내 전력시장", tabKorea],
  ["dc", "데이터센터·PPA", tabDatacenter],
  ["company", "기업 모니터", tabCompany],
  ["valuation", "밸류에이션", tabValuation],
  ["news", "뉴스·공시", tabNews],
  ["status", "데이터 상태", tabStatus],
];

/* ---- 1. 오늘의 결론 ---- */
function tabToday(root) {
  const b = DATA.brief || {};
  const p = el("div", "panel");
  p.appendChild(el("div", "panel-head",
    `<h3 class="panel-title">오늘 가장 중요한 변화</h3>
     <span class="panel-sub">기준일 ${esc(b.as_of || DATA.meta.as_of)} · 규칙 기반 자동생성</span>`));
  const hd = el("div", "brief-head");
  hd.appendChild(el("ul", "brief-list", (b.headline || []).map(h => `<li>${esc(h)}</li>`).join("")));
  p.appendChild(hd);
  root.appendChild(p);

  // 기업별 시그널
  const sp = el("div", "panel");
  sp.appendChild(el("div", "panel-head",
    `<h3 class="panel-title">기업별 시그널</h3>
     <span class="panel-sub">-5 ~ +5 정규화 점수 · 방향성 참고치이며 실적 확정치가 아님</span>`));
  const grid = el("div", "grid g4");
  COMPANIES.forEach(c => {
    const sc = ((DATA.signals || {}).companies || {})[c.id];
    const card = el("div", "sig-card");
    if (!sc) { card.innerHTML = `<div class="sig-name">${esc(c.name)}</div>
      <div class="muted" style="margin-top:8px">시그널 없음</div>`; grid.appendChild(card); return; }
    const col = sc.total > 1 ? "var(--up)" : sc.total < -1 ? "var(--down)" : "var(--flat)";
    const w = Math.min(50, Math.abs(sc.total) / 5 * 50);
    card.innerHTML = `<div class="sig-top">
        <div><div class="sig-name">${esc(c.name)}</div>
          <div class="sig-model">${esc(c.model)}</div></div>
        <div><div class="sig-score" style="color:${col}">${sc.total > 0 ? "+" : ""}${sc.total.toFixed(2)}</div>
          <div class="sig-delta ${cls(sc.delta)}" style="text-align:right">전주 ${sc.delta >= 0 ? "+" : ""}${sc.delta.toFixed(2)}</div></div>
      </div>
      <div class="sig-bar"><i style="background:${col};${sc.total >= 0
        ? `left:50%;width:${w}%` : `right:50%;width:${w}%`}"></i></div>
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px">
        <span class="badge ${sc.total > 1 ? "good" : sc.total < -1 ? "bad" : ""}">${esc(sc.verdict)}</span>
        <span class="muted" style="font-size:10.5px">지표 ${sc.signals_used}개 · 신뢰도 ${(sc.confidence * 100).toFixed(0)}%</span>
      </div>`;
    (sc.top_drivers || []).forEach(d => {
      card.appendChild(el("div", "sig-drv",
        `<span>${esc(d.label)}</span><span class="v ${cls(d.score)}">${pct(d.pct)} → ${d.score > 0 ? "+" : ""}${d.score}</span>`));
    });
    if ((sc.excluded || []).length) {
      card.appendChild(el("div", "sig-drv muted",
        `<span style="font-size:10.5px">제외 ${sc.excluded.length}개: ${
          esc(sc.excluded.slice(0, 3).map(e => e.label).join(", "))}</span>`));
    }
    grid.appendChild(card);
  });
  sp.appendChild(grid);
  sp.appendChild(el("div", "disclaimer",
    esc((DATA.signals || {}).disclaimer || "") +
    " 가중치는 사업구조에 대한 판단값으로 config/signals.yaml 에서 수정할 수 있습니다."));
  root.appendChild(sp);

  // 브리핑 섹션
  const sections = [["공급망", b.supply_chain], ["글로벌 수요", b.global_demand],
    ["국내", b.korea], ["오늘 확인할 이벤트", b.events]];
  const bp = el("div", "panel");
  bp.appendChild(el("div", "panel-head", `<h3 class="panel-title">아침 브리핑</h3>
    <span class="panel-sub">숫자와 비교기준이 없는 문장은 만들지 않습니다</span>`));
  const bg = el("div", "grid g2");
  sections.forEach(([name, obj]) => {
    if (!obj) return;
    const sec = el("div", "brief-sec");
    sec.appendChild(el("h4", null, esc(name)));
    Object.keys(obj).forEach(sub => {
      const items = obj[sub] || [];
      sec.appendChild(el("div", null, `<div style="font-size:11px;color:var(--ink-3);
        font-weight:700;margin-top:6px">${esc(sub)}</div>`));
      const ul = el("ul", "brief-list");
      items.forEach(it => {
        const li = el("li", it.ok === false ? "nodata" : "", esc(it.text));
        if (it.url) li.innerHTML = `<a href="${esc(it.url)}" target="_blank" rel="noopener">${esc(it.text)}</a>`;
        ul.appendChild(li);
      });
      sec.appendChild(ul);
    });
    bg.appendChild(sec);
  });
  bp.appendChild(bg);
  root.appendChild(bp);

  // 기업별 코멘트
  const cp = el("div", "panel");
  cp.appendChild(el("div", "panel-head", `<h3 class="panel-title">기업별 요약</h3>`));
  const cg = el("div", "grid g2");
  Object.entries(b.companies || {}).forEach(([name, c]) => {
    const box = el("div", "stat");
    box.innerHTML = `<div class="stat-label">${esc(name)} <span class="badge">${esc(c.verdict)}</span></div>
      <div class="muted" style="font-size:11px;margin:4px 0 6px">${esc(c.thesis || "")}</div>` +
      (c.lines || []).map(l => `<div style="font-size:11.5px;color:var(--ink-2);margin:2px 0">${esc(l)}</div>`).join("");
    cg.appendChild(box);
  });
  cp.appendChild(cg);
  root.appendChild(cp);
}

/* ---- 2. 공급망 가격 ---- */
function tabSupply(root) {
  const P = el("div", "panel");
  P.appendChild(el("div", "panel-head",
    `<h3 class="panel-title">폴리실리콘 → 웨이퍼 → 셀 → 모듈 가격</h3>
     <span class="panel-sub">단위가 다르므로 한 축에 겹쳐 그리지 않고 스몰멀티플로 표시</span>`));
  smallMultiples(P, [
    { title: "중국 N-type dense 폴리실리콘", metric: "poly_price_china_dense", entity: "CHN" },
    { title: "비중국산 폴리실리콘", metric: "poly_price_nonchina" },
    { title: "비중국산 프리미엄이 확대되는가", metric: "nonchina_poly_premium" },
    { title: "N-type M10 웨이퍼", metric: "wafer_price_m10", entity: "CHN" },
    { title: "M10 TOPCon 셀", metric: "cell_price_topcon_m10", entity: "CHN" },
    { title: "중국 모듈 FOB", metric: "module_price_china_fob", entity: "CHN" },
    { title: "미국 모듈 DDP", metric: "module_price_us_ddp", entity: "USA" },
    { title: "셀 가격 하락이 모듈 스프레드로 전가되는가", metric: "cell_module_spread" },
    { title: "미국-중국 모듈 가격차", metric: "us_china_module_premium" },
  ]);
  root.appendChild(P);

  // 변화율 표
  const ids = ["poly_price_china_dense", "poly_price_china_granular", "poly_price_nonchina",
    "nonchina_poly_premium", "wafer_price_m10", "wafer_price_g12", "wafer_price_210r",
    "cell_price_topcon_m10", "cell_price_topcon_g12", "module_price_china_fob",
    "module_price_eu_ddp", "module_price_us_ddp", "module_price_us_domestic",
    "cell_module_spread", "us_china_module_premium"];
  const rows = [];
  ids.forEach(m => seriesFor(m).forEach(s => rows.push(s)));

  const T = el("div", "panel");
  T.appendChild(el("div", "panel-head", `<h3 class="panel-title">가격 변화율</h3>
    <span class="panel-sub">WoW · 1M · 3M · 1Y — 관측치 간격 기준</span>`));
  if (!rows.length) {
    T.appendChild(emptyManual("공급망 가격"));
  } else {
    table(T, [
      { t: "지표", l: 1, k: "label", render: r => ({ html: esc(r.label), cls: "name" }) },
      { t: "최신", k: "latest", render: r => ({ html: `${fmt(r.latest)} <span class="muted">${esc(r.unit)}</span>` }) },
      { t: "WoW", k: "w", sortVal: r => (r.changes || {}).last,
        render: r => ({ html: pct((r.changes || {}).last), cls: cls((r.changes || {}).last) }) },
      { t: "1M", k: "m", sortVal: r => (r.changes || {}).m1,
        render: r => ({ html: pct((r.changes || {}).m1), cls: cls((r.changes || {}).m1) }) },
      { t: "3M", k: "q", sortVal: r => (r.changes || {}).m3,
        render: r => ({ html: pct((r.changes || {}).m3), cls: cls((r.changes || {}).m3) }) },
      { t: "1Y", k: "y", sortVal: r => (r.changes || {}).y1,
        render: r => ({ html: pct((r.changes || {}).y1), cls: cls((r.changes || {}).y1) }) },
      { t: "기준일", l: 1, k: "as_of", render: r => ({ html: `<span class="muted">${esc(r.as_of)}</span>` }) },
      { t: "출처", l: 1, k: "source",
        render: r => ({ html: `${tierBadge(r.tier, r.is_manual, r.is_estimate)} <span class="muted">${esc(r.source)}</span>` }) },
    ], rows);
  }
  root.appendChild(T);

  // 수혜 기업 매핑
  const M = el("div", "panel");
  M.appendChild(el("div", "panel-head", `<h3 class="panel-title">공급망 단계별 노출 기업</h3>
    <span class="panel-sub">사업구조 판단값 (추정 등급)</span>`));
  M.appendChild(exposureHeatmap(["polysilicon", "wafer", "cell", "module", "epc", "development", "generation", "ppa"]));
  root.appendChild(M);
}

function exposureHeatmap(keys) {
  const labels = DATA.exposure_labels || {};
  const box = el("div");
  const grid = el("div", "heat");
  grid.style.gridTemplateColumns = `120px repeat(${keys.length}, minmax(0,1fr))`;
  grid.appendChild(el("div", "heat-lbl", ""));
  keys.forEach(k => grid.appendChild(el("div", "heat-lbl",
    `<span style="writing-mode:horizontal-tb">${esc(labels[k] || k)}</span>`)));
  COMPANIES.forEach(c => {
    grid.appendChild(el("div", "heat-lbl", `<b style="color:var(--ink)">${esc(c.name)}</b>`));
    keys.forEach(k => {
      const v = (c.exposure || {})[k] || 0;
      const bg = v === 3 ? "rgba(46,196,166,.55)" : v === 2 ? "rgba(46,196,166,.32)"
        : v === 1 ? "rgba(46,196,166,.14)" : "transparent";
      const txt = v === 3 ? "핵심" : v === 2 ? "일부" : v === 1 ? "간접" : "·";
      const cell = el("div", "heat-cell", txt);
      cell.style.background = bg;
      cell.style.color = v >= 2 ? "var(--ink)" : "var(--ink-3)";
      cell.style.border = "1px solid var(--line-soft)";
      grid.appendChild(cell);
    });
  });
  box.appendChild(grid);
  return box;
}

/* ---- 3. 글로벌 수요 ---- */
function tabGlobal(root) {
  const CN = { KOR: "한국", USA: "미국", CHN: "중국", IND: "인도", DEU: "독일", JPN: "일본", EU27: "EU27" };
  const kp = el("div", "panel");
  kp.appendChild(el("div", "panel-head", `<h3 class="panel-title">주요국 태양광 현황</h3>
    <span class="panel-sub">최신 연간 기준</span>`));
  const kg = el("div", "grid g4");
  ["USA", "CHN", "IND", "KOR"].forEach(c => {
    const s = S("solar_share_pct", c);
    const t = statTile(s, { label: `${CN[c]} 전력믹스 내 태양광 비중` });
    kg.appendChild(t);
  });
  kp.appendChild(kg);
  root.appendChild(kp);

  const c1 = el("div", "panel");
  c1.appendChild(el("div", "panel-head", `<h3 class="panel-title">월간 태양광 발전량 — 국가별 성장 속도</h3>`));
  chart(c1, seriesFor("solar_generation_monthly_twh").map((s, i) => ({ ...s, label: CN[s.entity] || s.entity })),
    { title: "월간 태양광 발전량", height: 250, defaultDays: 1095, allowMixed: true });
  root.appendChild(c1);

  const g = el("div", "grid g2");
  const c2 = el("div", "panel");
  c2.appendChild(el("div", "panel-head", `<h3 class="panel-title">누적 설비용량</h3>`));
  chart(c2, seriesFor("solar_capacity_gw").map(s => ({ ...s, label: CN[s.entity] || s.entity })),
    { title: "누적 태양광 설비용량", height: 210, defaultDays: 0, allowMixed: true });
  g.appendChild(c2);

  const c3 = el("div", "panel");
  c3.appendChild(el("div", "panel-head", `<h3 class="panel-title">전력믹스 내 태양광 비중</h3>`));
  chart(c3, seriesFor("solar_share_pct").map(s => ({ ...s, label: CN[s.entity] || s.entity })),
    { title: "태양광 발전 비중", height: 210, defaultDays: 0, allowMixed: true });
  g.appendChild(c3);
  root.appendChild(g);

  const c4 = el("div", "panel");
  c4.appendChild(el("div", "panel-head", `<h3 class="panel-title">미국 태양광 — 발전량·모듈 출하</h3>
    <span class="panel-sub">EIA. API 키가 없으면 비어 있습니다</span>`));
  const us = [S("us_solar_generation_gwh", "USA"), S("us_module_shipments_mw", "USA")].filter(Boolean);
  if (us.length) {
    chart(c4, us, { title: "미국 태양광 지표", height: 220, normalize: true });
  } else {
    c4.appendChild(el("div", "empty", `<b>EIA 데이터 없음</b>
      <code>EIA_API_KEY</code> 를 <code>.env</code> 에 넣으면 자동으로 채워집니다.
      무료 발급: <a href="https://www.eia.gov/opendata/register.php" target="_blank" rel="noopener">eia.gov/opendata/register</a>`));
  }
  root.appendChild(c4);

  const c5 = el("div", "panel");
  c5.appendChild(el("div", "panel-head", `<h3 class="panel-title">전력수요 대비 태양광 — 수요 증가를 따라잡고 있는가</h3>`));
  chart(c5, seriesFor("electricity_demand_monthly_twh").map(s => ({ ...s, label: CN[s.entity] || s.entity })),
    { title: "월간 전력수요", height: 210, defaultDays: 1095, allowMixed: true });
  root.appendChild(c5);
}

/* ---- 4. 국내 전력시장 ---- */
function tabKorea(root) {
  const REG = { seoul: "서울", gyeonggi: "경기", chungnam: "충남", jeonbuk: "전북",
    jeonnam: "전남", gyeongbuk: "경북", jeju: "제주" };

  const kp = el("div", "panel");
  kp.appendChild(el("div", "panel-head", `<h3 class="panel-title">국내 태양광 수익환경</h3>`));
  const kg = el("div", "grid g4");
  kg.appendChild(statTile(S("smp_land", "KOR"), { label: "육지 SMP", hint: "KPX API 활용신청 필요" }));
  kg.appendChild(statTile(S("rec_spot_price", "KOR"), { label: "REC 현물가", hint: "KPX API 활용신청 필요" }));
  kg.appendChild(statTile(S("smp_rec_revenue", "KOR"), { label: "SMP+REC 환산수익", hint: "SMP·REC 수집 후 자동계산" }));
  kg.appendChild(statTile(S("kr_solar_generation", "KOR"), { label: "국내 태양광 발전량", hint: "KPX API 활용신청 필요" }));
  kp.appendChild(kg);

  const smp = [S("smp_land", "KOR"), S("smp_jeju", "KOR"), S("smp_rec_revenue", "KOR")].filter(Boolean);
  if (smp.length) {
    chart(kp, smp, { title: "국내 SMP+REC 수익환경", height: 230, defaultDays: 365 });
  } else {
    kp.appendChild(el("div", "empty", `<b>SMP·REC 데이터 없음</b>
      보유 중인 data.go.kr 키는 유효하지만 KPX API 개별 <b>활용신청</b>이 필요합니다.<br>
      <a href="https://www.data.go.kr" target="_blank" rel="noopener">data.go.kr</a> 에서
      "한국전력거래소 계통한계가격(SMP)" 활용신청 후 승인되면 같은 키로 자동 수집됩니다.`));
  }
  kp.appendChild(el("div", "disclaimer",
    "SMP+REC 환산수익은 1 REC = 1MWh 단순 환산에 REC 가중치 기본 1.0 을 적용한 " +
    "시장가격 기반 참고치입니다. REC 가중치는 프로젝트마다 다르므로 실제 계약수익과 다릅니다."));
  root.appendChild(kp);

  // 일사량
  const ip = el("div", "panel");
  ip.appendChild(el("div", "panel-head", `<h3 class="panel-title">권역별 일사량 — 발전여건</h3>
    <span class="panel-sub">Open-Meteo 실측·예보 + NASA POWER 평년 (실측과 예보는 구분해 저장)</span>`));
  const irr = seriesFor("ghi_daily").map(s => ({ ...s, label: REG[s.entity] || s.entity }));
  chart(ip, irr, { title: "일평균 수평면 일사량(GHI)", height: 230, defaultDays: 91, allowMixed: true });
  root.appendChild(ip);

  const dp = el("div", "panel");
  dp.appendChild(el("div", "panel-head", `<h3 class="panel-title">평년 대비 일사량</h3>
    <span class="panel-sub">NASA POWER 장기평년 대비 최근 7일·30일</span>`));
  const dev = seriesFor("ghi_normal_dev_pct");
  if (dev.length) {
    const rows = dev.map(s => ({ ...s, region: REG[s.entity] || s.entity }));
    table(dp, [
      { t: "권역", l: 1, k: "region", render: r => ({ html: esc(r.region), cls: "name" }) },
      { t: "평년대비", k: "latest", render: r => ({ html: pct(r.latest), cls: cls(r.latest) }) },
      { t: "기준일", l: 1, k: "as_of", render: r => ({ html: `<span class="muted">${esc(r.as_of)}</span>` }) },
      { t: "설명", l: 1, k: "note", render: r => ({ html: `<span class="muted">${esc(r.note)}</span>`, cls: "wrap" }) },
    ], rows, { sortBy: 1 });
  } else {
    dp.appendChild(el("div", "empty", "<b>평년 대비 데이터 없음</b>NASA POWER 평년값 수집 후 계산됩니다."));
  }
  root.appendChild(dp);

  const sp = el("div", "panel");
  sp.appendChild(el("div", "panel-head", `<h3 class="panel-title">권역별 일조시간</h3>`));
  chart(sp, seriesFor("sunshine_hours").map(s => ({ ...s, label: REG[s.entity] || s.entity })),
    { title: "일조시간", height: 200, defaultDays: 91, allowMixed: true });
  root.appendChild(sp);
}

/* ---- 5. 데이터센터·PPA ---- */
function tabDatacenter(root) {
  const deals = DATA.ppa_deals || [];
  const P = el("div", "panel");
  P.appendChild(el("div", "panel-head", `<h3 class="panel-title">데이터센터향 태양광·ESS PPA</h3>
    <span class="panel-sub">공식 발표(official=1)만 확정 집계 — 기대·추정 물량은 분리</span>`));

  if (!deals.length) {
    P.appendChild(el("div", "empty", `<b>PPA 계약 데이터가 아직 없습니다</b>
      공식 보도자료·지속가능성보고서·규제기관 자료를 확인해
      <code>data/manual/ppa_deals_manual.csv</code> 에 입력하면 집계·차트가 생성됩니다.<br>
      기사 전문을 저장하지 말고 제목·날짜·링크·짧은 요약만 기록하세요.`));
    root.appendChild(P);
    return;
  }

  const num = (d, k) => { const v = parseFloat(d[k]); return isNaN(v) ? 0 : v; };
  const confirmed = deals.filter(d => String(d.official) === "1");
  const expected = deals.filter(d => String(d.official) !== "1");
  const dcLinked = confirmed.filter(d => String(d.datacenter_linked) === "1");

  const g = el("div", "grid g4");
  const mk = (label, val, sub) => {
    const b = el("div", "stat");
    b.innerHTML = `<div class="stat-label">${esc(label)}</div>
      <div class="stat-val">${fmt(val)}<span class="u">MW</span></div>
      <div class="stat-sub muted">${esc(sub)}</div>`;
    return b;
  };
  g.appendChild(mk("확정 데이터센터 연계 태양광", dcLinked.reduce((a, d) => a + num(d, "solar_mw"), 0), `${dcLinked.length}건`));
  g.appendChild(mk("확정 전체 태양광", confirmed.reduce((a, d) => a + num(d, "solar_mw"), 0), `${confirmed.length}건`));
  const essTotal = confirmed.reduce((a, d) => a + num(d, "ess_mwh"), 0);
  const eb = el("div", "stat");
  eb.innerHTML = `<div class="stat-label">확정 ESS</div>
    <div class="stat-val">${fmt(essTotal)}<span class="u">MWh</span></div>
    <div class="stat-sub muted">태양광+ESS ${confirmed.filter(d => num(d, "ess_mwh") > 0).length}건</div>`;
  g.appendChild(eb);
  g.appendChild(mk("기대·추정 (확정 아님)", expected.reduce((a, d) => a + num(d, "solar_mw"), 0), `${expected.length}건 · 집계 제외`));
  P.appendChild(g);
  root.appendChild(P);

  // 연도별 / 구매자별
  const byYear = {}, byBuyer = {};
  dcLinked.forEach(d => {
    const y = String(d.announced_date || "").slice(0, 4);
    if (y) byYear[y] = (byYear[y] || 0) + num(d, "solar_mw");
    const b = d.buyer || "미상";
    byBuyer[b] = (byBuyer[b] || 0) + num(d, "solar_mw");
  });

  const cg = el("div", "grid g2");
  const y1 = el("div", "panel");
  y1.appendChild(el("div", "panel-head", `<h3 class="panel-title">연도별 데이터센터 연계 태양광 PPA</h3>`));
  chart(y1, [{ label: "확정 계약 MW", unit: "MW", entity: "GLOBAL", source: "수기입력 (공식 발표)",
    as_of: DATA.meta.as_of, freq: "irregular", tier: 3,
    points: Object.keys(byYear).sort().map(y => [y, byYear[y]]) }],
    { title: "연도별 계약 용량", height: 200, kind: "bar", defaultDays: 0, zeroBase: true });
  cg.appendChild(y1);

  const b1 = el("div", "panel");
  b1.appendChild(el("div", "panel-head", `<h3 class="panel-title">구매자별 누적 계약</h3>`));
  const brows = Object.entries(byBuyer).map(([k, v]) => ({ buyer: k, mw: v }));
  table(b1, [
    { t: "구매자", l: 1, k: "buyer", render: r => ({ html: esc(r.buyer), cls: "name" }) },
    { t: "태양광 MW", k: "mw", render: r => ({ html: fmt(r.mw) }) },
  ], brows, { sortBy: 1 });
  cg.appendChild(b1);
  root.appendChild(cg);

  // 계약 목록
  const L = el("div", "panel");
  L.appendChild(el("div", "panel-head", `<h3 class="panel-title">계약 목록</h3>`));
  const rows = deals.map(d => ({ ...d, _search: [d.buyer, d.developer, d.country, d.summary].join(" ") }));
  table(L, [
    { t: "발표일", l: 1, k: "announced_date" },
    { t: "구매자", l: 1, k: "buyer", render: r => ({ html: esc(r.buyer), cls: "name" }) },
    { t: "발전사업자", l: 1, k: "developer", render: r => ({ html: esc(r.developer || "-") }) },
    { t: "국가", l: 1, k: "country" },
    { t: "태양광", k: "solar_mw", sortVal: r => num(r, "solar_mw"),
      render: r => ({ html: fmt(num(r, "solar_mw")) + " MW" }) },
    { t: "ESS", k: "ess_mwh", sortVal: r => num(r, "ess_mwh"),
      render: r => ({ html: num(r, "ess_mwh") ? fmt(num(r, "ess_mwh")) + " MWh" : "-" }) },
    { t: "구분", l: 1, k: "contract_type" },
    { t: "확정", l: 1, k: "official", render: r => ({
      html: String(r.official) === "1" ? '<span class="badge good">공식</span>'
        : '<span class="badge est">기대·추정</span>' }) },
    { t: "DC", l: 1, k: "datacenter_linked", render: r => ({
      html: String(r.datacenter_linked) === "1" ? "○" : "-" }) },
    { t: "출처", l: 1, k: "source_name", render: r => ({
      html: r.source_url ? `<a href="${esc(r.source_url)}" target="_blank" rel="noopener">${esc(r.source_name || "링크")}</a>`
        : esc(r.source_name || "-") }) },
  ], rows, { sortBy: 0 });
  root.appendChild(L);
}

/* ---- 6. 기업 모니터 ---- */
function tabCompany(root) {
  // 주가 상대비교
  const P = el("div", "panel");
  P.appendChild(el("div", "panel-head", `<h3 class="panel-title">주가 상대수익률</h3>
    <span class="panel-sub">기간 시작일 = 100 정규화</span>`));
  chart(P, seriesFor("close_price").map(s => ({ ...s, label: CNAME[s.entity] || s.entity })),
    { title: "주가 (100 기준 정규화)", height: 260, normalize: true, defaultDays: 365 });
  root.appendChild(P);

  COMPANIES.forEach(c => {
    const sc = ((DATA.signals || {}).companies || {})[c.id] || {};
    const p = el("div", "panel");
    p.appendChild(el("div", "panel-head",
      `<h3 class="panel-title">${esc(c.name)} <span class="muted" style="font-weight:400;font-size:11px">${esc(c.stock_code)}</span></h3>
       <span class="panel-sub">${esc(c.model)} · ${esc(c.thesis)}</span>`));

    const g = el("div", "grid g4");
    const price = S("close_price", c.id);
    g.appendChild(statTile(price, { label: "주가" }));
    g.appendChild(statTile(S("revenue_q", c.id), { label: "분기 매출" }));
    g.appendChild(statTile(S("op_profit_q", c.id), { label: "분기 영업이익" }));
    g.appendChild(statTile(S("op_margin_q", c.id), { label: "영업이익률" }));
    p.appendChild(g);

    // 52주 고점 대비
    if (price && price.points.length > 20) {
      const yr = Date.now() - 365 * 864e5;
      const win = price.points.filter(pt => pdate(pt[0]).getTime() >= yr).map(pt => pt[1]);
      if (win.length) {
        const hi = Math.max(...win), lo = Math.min(...win), cur = price.latest;
        const gap = (cur - hi) / hi * 100;
        p.appendChild(el("div", "stat-sub", `<span class="muted">52주 고점 ${fmt(hi)}원 대비</span>
          <span class="${cls(gap)}">${pct(gap)}</span>
          <span class="muted">· 52주 저점 ${fmt(lo)}원</span>`));
      }
    }

    // 실적 차트
    const fin = [S("revenue_q", c.id), S("op_profit_q", c.id)].filter(Boolean);
    if (fin.length) {
      chart(p, fin, { title: "분기 실적 (누적→단독분기 환산)", height: 190, defaultDays: 1095, allowMixed: true });
    }

    // 시그널 드라이버
    if (sc.all_drivers && sc.all_drivers.length) {
      const d = el("div");
      d.appendChild(el("div", null, `<div style="font-size:11px;color:var(--ink-3);
        font-weight:700;margin:10px 0 4px">산업 KPI 민감도 — 시그널 기여도</div>`));
      table(d, [
        { t: "지표", l: 1, k: "label", render: r => ({ html: esc(r.label), cls: "name" }) },
        { t: "변화", k: "pct", render: r => ({ html: pct(r.pct), cls: cls(r.pct) }) },
        { t: "점수", k: "score", render: r => ({ html: (r.score > 0 ? "+" : "") + r.score, cls: cls(r.score) }) },
        { t: "가중치", k: "weight" },
        { t: "기여도", k: "contribution", render: r => ({
          html: (r.contribution > 0 ? "+" : "") + r.contribution.toFixed(2), cls: cls(r.contribution) }) },
        { t: "근거", l: 1, k: "rationale", render: r => ({ html: `<span class="muted">${esc(r.rationale)}</span>`, cls: "wrap" }) },
      ], sc.all_drivers.slice());
      p.appendChild(d);
    }
    if ((sc.excluded || []).length) {
      p.appendChild(el("div", "disclaimer", "데이터 부족·노후로 제외된 지표: " +
        esc(sc.excluded.map(e => `${e.label}(${e.reason})`).join(", "))));
    }

    // 최근 공시
    const f = (DATA.filings || []).filter(x => x.company_id === c.id).slice(0, 6);
    if (f.length) {
      const fl = el("ul", "clean");
      fl.style.cssText = "margin-top:10px;font-size:11.5px";
      f.forEach(x => fl.appendChild(el("li", null,
        `<span class="muted num">${esc(x.date)}</span>
         <span class="badge">${esc(x.kind)}</span>
         <a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.title)}</a>`)));
      p.appendChild(fl);
    }
    root.appendChild(p);
  });

  const H = el("div", "panel");
  H.appendChild(el("div", "panel-head", `<h3 class="panel-title">밸류체인 노출도</h3>
    <span class="panel-sub">사업구조 판단값 — 추정 등급</span>`));
  H.appendChild(exposureHeatmap(Object.keys(DATA.exposure_labels || {})));
  root.appendChild(H);
}

/* ---- 7. 밸류에이션 ---- */
function tabValuation(root) {
  const P = el("div", "panel");
  P.appendChild(el("div", "panel-head", `<h3 class="panel-title">밸류에이션</h3>
    <span class="panel-sub">자동 수집 불가 항목은 지어내지 않고 '데이터 없음'으로 표시</span>`));

  const rows = COMPANIES.map(c => {
    const price = S("close_price", c.id);
    const rev = S("revenue_q", c.id), op = S("op_profit_q", c.id);
    // 최근 4개 분기 합산 (LTM)
    const ltm = s => {
      if (!s || s.points.length < 4) return null;
      return s.points.slice(-4).reduce((a, p) => a + p[1], 0);
    };
    return {
      name: c.name, id: c.id, code: c.stock_code,
      multiples: (c.key_multiples || []).join(", "),
      price: price ? price.latest : null,
      ltm_rev: ltm(rev), ltm_op: ltm(op),
      mcap: S("market_cap", c.id) ? S("market_cap", c.id).latest : null,
      per: null, pbr: null, ev_ebitda: null,
    };
  });

  table(P, [
    { t: "기업", l: 1, k: "name", render: r => ({ html: esc(r.name), cls: "name" }) },
    { t: "주가", k: "price", render: r => ({ html: r.price ? fmt(r.price) + "원" : '<span class="muted">-</span>' }) },
    { t: "시가총액", k: "mcap", render: r => ({
      html: r.mcap ? fmt(r.mcap) + "십억원" : '<span class="muted">데이터 없음</span>' }) },
    { t: "LTM 매출", k: "ltm_rev", render: r => ({
      html: r.ltm_rev != null ? fmt(r.ltm_rev) + "십억원" : '<span class="muted">-</span>' }) },
    { t: "LTM 영업이익", k: "ltm_op", render: r => ({
      html: r.ltm_op != null ? fmt(r.ltm_op) + "십억원" : '<span class="muted">-</span>' }) },
    { t: "PER", k: "per", render: r => ({ html: '<span class="muted">데이터 없음</span>' }) },
    { t: "PBR", k: "pbr", render: r => ({ html: '<span class="muted">데이터 없음</span>' }) },
    { t: "EV/EBITDA", k: "ev_ebitda", render: r => ({ html: '<span class="muted">데이터 없음</span>' }) },
    { t: "핵심 멀티플", l: 1, k: "multiples", render: r => ({ html: `<span class="muted">${esc(r.multiples)}</span>`, cls: "wrap" }) },
  ], rows);

  P.appendChild(el("div", "disclaimer",
    "시가총액·PER·PBR·EV/EBITDA 는 발행주식수와 컨센서스가 있어야 계산됩니다. " +
    "컨센서스는 유료 데이터(FnGuide 등)라 자동 수집하지 않습니다. " +
    "data/manual/manual_estimates.csv 에 입력하면 이 표에 반영되고, 없으면 '데이터 없음'으로 남습니다. " +
    "12개월 선행 값은 컨센서스가 있을 때만 표시합니다."));
  root.appendChild(P);

  // 추정치가 입력돼 있으면 표시
  const estRows = [];
  ["revenue_est", "op_profit_est", "net_profit_est", "ebitda_est", "per_fwd", "pbr_fwd", "ev_ebitda_fwd"]
    .forEach(m => seriesFor(m).forEach(s => estRows.push(s)));
  const E = el("div", "panel");
  E.appendChild(el("div", "panel-head", `<h3 class="panel-title">입력된 추정치·컨센서스</h3>`));
  if (!estRows.length) {
    E.appendChild(el("div", "empty", `<b>입력된 추정치 없음</b>
      <code>data/manual/manual_estimates.csv</code> 를 채우면 표시됩니다.`));
  } else {
    table(E, [
      { t: "기업", l: 1, k: "entity", render: r => ({ html: esc(CNAME[r.entity] || r.entity), cls: "name" }) },
      { t: "지표", l: 1, k: "label" },
      { t: "값", k: "latest", render: r => ({ html: `${fmt(r.latest)} <span class="muted">${esc(r.unit)}</span>` }) },
      { t: "기간", l: 1, k: "as_of" },
      { t: "출처", l: 1, k: "source", render: r => ({ html: `${tierBadge(r.tier, r.is_manual, true)} ${esc(r.source)}` }) },
    ], estRows);
  }
  root.appendChild(E);
}

/* ---- 8. 뉴스·공시 ---- */
function tabNews(root) {
  const f = DATA.filings || [];
  const P = el("div", "panel");
  P.appendChild(el("div", "panel-head", `<h3 class="panel-title">공시 (OpenDART)</h3>
    <span class="panel-sub">최근 ${f.length}건</span>`));
  if (!f.length) {
    P.appendChild(el("div", "empty", "<b>공시 없음</b>DART 수집이 실패했거나 조회 기간에 공시가 없습니다."));
  } else {
    const rows = f.map(x => ({ ...x, _search: [x.company, x.title, x.kind].join(" ") }));
    table(P, [
      { t: "일자", l: 1, k: "date" },
      { t: "기업", l: 1, k: "company", render: r => ({ html: esc(r.company), cls: "name" }) },
      { t: "구분", l: 1, k: "kind", render: r => ({ html: `<span class="badge">${esc(r.kind)}</span>` }) },
      { t: "제목", l: 1, k: "title", render: r => ({
        html: `<a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.title)}</a>`, cls: "wrap" }) },
      { t: "제출인", l: 1, k: "filer", render: r => ({ html: `<span class="muted">${esc(r.filer)}</span>` }) },
    ], rows, { sortBy: 0 });
  }
  root.appendChild(P);

  const N = el("div", "panel");
  N.appendChild(el("div", "panel-head", `<h3 class="panel-title">뉴스</h3>`));
  N.appendChild(el("div", "empty", `<b>뉴스 수집 미설정</b>
    네이버 검색 API 키(<code>NAVER_CLIENT_ID</code>, <code>NAVER_CLIENT_SECRET</code>)를
    <code>.env</code> 에 넣으면 활성화할 수 있습니다.
    저작권 보호를 위해 제목·날짜·링크·짧은 요약만 저장하고 기사 전문은 저장하지 않습니다.`));
  root.appendChild(N);
}

/* ---- 9. 데이터 상태 ---- */
function tabStatus(root) {
  const st = DATA.status || [];
  const P = el("div", "panel");
  const sm = DATA.meta.source_summary || {};
  P.appendChild(el("div", "panel-head", `<h3 class="panel-title">소스별 수집 상태</h3>
    <span class="panel-sub">정상 ${sm.ok} · 지연 ${sm.stale} · 오류 ${sm.error} ·
      키없음 ${sm.no_key} · 미입력 ${sm.manual_empty}</span>`));
  const g = el("div", "grid g3");
  const LBL = { ok: "정상", stale: "지연", error: "오류", no_key: "API 미설정",
    manual_empty: "수기입력 대기", disabled: "비활성" };
  st.forEach(s => {
    const c = el("div", "st-card " + s.state);
    c.dataset.search = [s.label, s.source_id, s.message].join(" ");
    c.innerHTML = `
      <div class="st-name"><span>${esc(s.label)}</span>
        <span class="badge ${s.state === "ok" ? "good" : s.state === "error" ? "bad" : ""}">${esc(LBL[s.state] || s.state)}</span></div>
      <div class="st-row"><span>원 데이터 발표주기</span><b>${esc(s.frequency)}</b></div>
      <div class="st-row"><span>원 데이터 기준일</span><b>${esc(s.latest_as_of || "-")}</b></div>
      <div class="st-row"><span>마지막 수집 성공</span><b>${esc((s.last_success || "-").replace("T", " "))}</b></div>
      <div class="st-row"><span>다음 예상 갱신</span><b>${esc(s.next_expected || "-")}</b></div>
      <div class="st-row"><span>포인트 / 지연기준</span><b>${s.points} / ${s.stale_days}일</b></div>
      <div class="st-row"><span>출처등급</span><b>${(DATA.meta.tier_labels || {})[String(s.tier)] || s.tier}</b></div>
      ${s.message ? `<div class="st-msg">${esc(s.message)}</div>` : ""}
      ${s.signup ? `<div class="st-msg">발급/신청: <a href="${esc(s.signup)}" target="_blank" rel="noopener">${esc(s.signup)}</a></div>` : ""}`;
    g.appendChild(c);
  });
  P.appendChild(g);
  root.appendChild(P);

  // 품질 보고서
  const q = DATA.quality || {};
  const Q = el("div", "panel");
  const qs = q.summary || {};
  Q.appendChild(el("div", "panel-head", `<h3 class="panel-title">데이터 품질 보고서</h3>
    <span class="panel-sub">총 ${qs.total || 0}건 · 드롭 ${qs.dropped || 0}건</span>`));
  const issues = (q.issues || []).filter(i => i.severity !== "info");
  if (!issues.length) {
    Q.appendChild(el("div", "empty", "<b>주요 품질 이슈 없음</b>error·warn 등급 위반이 없습니다."));
  } else {
    table(Q, [
      { t: "등급", l: 1, k: "severity", render: r => ({
        html: `<span class="badge ${r.severity === "error" ? "bad" : ""}">${esc(r.severity)}</span>` }) },
      { t: "종류", l: 1, k: "kind" },
      { t: "지표", l: 1, k: "metric_id", render: r => ({ html: esc(r.metric_id || "-"), cls: "name" }) },
      { t: "대상", l: 1, k: "entity", render: r => ({ html: esc(CNAME[r.entity] || r.entity || "-") }) },
      { t: "기간", l: 1, k: "period" },
      { t: "내용", l: 1, k: "detail", render: r => ({ html: esc(r.detail), cls: "wrap" }) },
      { t: "드롭", l: 1, k: "dropped", render: r => ({ html: r.dropped ? "○" : "-" }) },
    ], issues.slice(0, 200));
  }
  root.appendChild(Q);

  const M = el("div", "panel");
  M.appendChild(el("div", "panel-head", `<h3 class="panel-title">수기 입력 현황</h3>`));
  M.appendChild(el("div", "disclaimer",
    "자동 수집이 불가능한 유료·구독 데이터는 우회하지 않습니다. " +
    "data/manual/ 의 CSV 템플릿을 채우면 다음 실행에서 자동 반영됩니다. " +
    "SAMPLE 로 표시된 예시 행은 대시보드에 포함되지 않습니다."));
  root.appendChild(M);
}

/* ============================ 부팅 ============================ */
function renderMeta() {
  const m = DATA.meta, s = m.source_summary || {};
  const chips = [
    `<span class="mchip">기준일 <b>${esc(m.as_of)}</b></span>`,
    `<span class="mchip">갱신 <b>${esc((m.generated_at || "").replace("T", " "))}</b></span>`,
    `<span class="mchip ok">정상 <b>${s.ok}</b></span>`,
  ];
  if (s.stale) chips.push(`<span class="mchip warn">지연 <b>${s.stale}</b></span>`);
  if (s.error) chips.push(`<span class="mchip bad">오류 <b>${s.error}</b></span>`);
  if (s.no_key) chips.push(`<span class="mchip">API 미설정 <b>${s.no_key}</b></span>`);
  if (s.manual_empty) chips.push(`<span class="mchip">수기입력 대기 <b>${s.manual_empty}</b></span>`);
  chips.push(`<span class="mchip">시리즈 <b>${m.series_count}</b> · 포인트 <b>${(m.point_count || 0).toLocaleString()}</b></span>`);
  $("#metaChips").innerHTML = chips.join("");
}

let current = "today";
function show(id) {
  current = id;
  [...$("#tabs").children].forEach(b => b.setAttribute("aria-selected", String(b.dataset.id === id)));
  const shell = $("#shell");
  shell.innerHTML = "";
  const def = TABS.find(t => t[0] === id);
  try {
    def[2](shell);
  } catch (e) {
    shell.appendChild(el("div", "panel", `<div class="empty"><b>화면 렌더 오류</b>
      ${esc(e.message)}<br><span class="muted">이 탭만 실패했고 나머지는 정상입니다.</span></div>`));
    console.error(e);
  }
  applySearch();
  location.hash = id;
}

function applySearch() {
  const q = $("#search").value.trim().toLowerCase();
  document.querySelectorAll("[data-search]").forEach(n => {
    n.classList.toggle("hidden", !!q && !n.dataset.search.toLowerCase().includes(q));
  });
  document.querySelectorAll("tbody tr").forEach(tr => {
    if (tr.dataset.search) return;
    if (!q) { tr.classList.remove("hidden"); return; }
    tr.classList.toggle("hidden", !tr.textContent.toLowerCase().includes(q));
  });
}

function downloadCsv() {
  const lines = [["metric_id", "entity", "label", "period", "value", "unit",
    "as_of", "source", "tier", "is_manual", "is_estimate"].join(",")];
  const q = (s) => `"${String(s == null ? "" : s).replace(/"/g, '""')}"`;
  Object.values(DATA.series).forEach(s => {
    s.points.forEach(p => lines.push([q(s.metric_id), q(s.entity), q(s.label), q(p[0]), p[1],
      q(s.unit), q(s.as_of), q(s.source), s.tier, s.is_manual ? 1 : 0, s.is_estimate ? 1 : 0].join(",")));
  });
  const blob = new Blob(["﻿" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `solar_terminal_${DATA.meta.as_of}.csv`;
  a.click(); URL.revokeObjectURL(a.href);
}

(function init() {
  renderMeta();
  const tabs = $("#tabs");
  TABS.forEach(([id, label]) => {
    const b = el("button", "tab", esc(label));
    b.dataset.id = id;
    b.onclick = () => show(id);
    tabs.appendChild(b);
  });
  // 현재 테마는 속성만 보고 판단하면 안 된다. 게시 환경에서는 뷰어가 루트에
  // data-theme 를 찍고, 속성이 없으면 OS 선호를 따른다. 둘 다 봐야 버튼이
  // 거꾸로 동작하지 않는다.
  function isDark() {
    const a = document.documentElement.getAttribute("data-theme");
    if (a === "dark") return true;
    if (a === "light") return false;
    return window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches;
  }
  function syncThemeLabel() {
    $("#btnTheme").textContent = isDark() ? "라이트" : "다크";
  }
  syncThemeLabel();

  $("#btnTheme").onclick = () => {
    document.documentElement.dataset.theme = isDark() ? "light" : "dark";
    syncThemeLabel();
    show(current);
  };

  // 뷰어가 바깥에서 테마를 바꾸면 차트 색을 다시 계산해야 한다
  new MutationObserver(() => { syncThemeLabel(); show(current); })
    .observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  $("#btnCsv").onclick = downloadCsv;
  $("#search").addEventListener("input", applySearch);
  addEventListener("scroll", hideTip, { passive: true });

  const hash = location.hash.replace("#", "");
  show(TABS.some(t => t[0] === hash) ? hash : "today");
})();
</script>
</body>
</html>
"""
