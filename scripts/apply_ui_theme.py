from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
LINK = '<link rel="stylesheet" href="./ui.css">'

NAV = """<nav class="terminal-nav" aria-label="Primary navigation">
  <details class="terminal-nav-group"><summary>MARKET</summary>
    <a href="./index.html">Market Overview</a>
    <a href="./index.html#screener">Screener</a>
    <a href="./heatmap.html">Heatmap</a>
    <a href="./sector-rotation.html">Sector Rotation</a>
    <a href="./volume-intelligence.html">Volume Intelligence</a>
  </details>
  <details class="terminal-nav-group"><summary>RESEARCH</summary>
    <a href="./fundamental.html">Fundamental</a>
    <a href="./teknikal.html">Technical</a>
    <a href="./value-gap.html">Value Gap</a>
    <a href="./relative-strength.html">Relative Strength</a>
    <a href="./market-intelligence.html">Market Intelligence</a>
  </details>
  <details class="terminal-nav-group"><summary>SIGNALS</summary>
    <a href="./early-signals.html">Early Signals</a>
    <a href="./technical-journal.html">Technical Trade Journal</a>
    <a href="./recommendations.html">Recommendations</a>
    <a href="./recommendation-analytics.html">Recommendation Analytics</a>
  </details>
  <details class="terminal-nav-group"><summary>QUANT</summary>
    <a href="./backtest.html">Backtest All Setup</a>
    <a href="./momentum-dashboard.html">Momentum Dashboard</a>
    <a href="./catalyst-calendar.html">Catalyst Calendar</a>
  </details>
  <details class="terminal-nav-group"><summary>SYSTEM</summary>
    <a href="./stock-detail.html">Stock Detail</a>
    <a href="./system-health.html">System Health</a>
    <a href="./admin.html">Admin</a>
  </details>
</nav>"""

SIDEBAR = """<aside class="terminal-sidebar" aria-label="Quant research terminal navigation">
  <div class="terminal-sidebar-brand"><span>SPC</span><b>QUANT RESEARCH</b><small>MARKET ANALYTICS WORKSTATION</small></div>
  <div class="terminal-sidebar-section">
    <div class="terminal-sidebar-title">MARKET</div>
    <a class="active" href="./index.html">Market Overview</a>
    <a href="./index.html#screener">Screener</a>
    <a href="./heatmap.html">Heatmap</a>
    <a href="./sector-rotation.html">Sector Rotation</a>
    <a href="./volume-intelligence.html">Volume Intelligence</a>
  </div>
  <div class="terminal-sidebar-section">
    <div class="terminal-sidebar-title">RESEARCH</div>
    <a href="./fundamental.html">Fundamental</a><a href="./teknikal.html">Technical</a>
    <a href="./value-gap.html">Value Gap</a><a href="./relative-strength.html">Relative Strength</a>
    <a href="./market-intelligence.html">Market Intelligence</a>
  </div>
  <div class="terminal-sidebar-section">
    <div class="terminal-sidebar-title">SIGNALS</div>
    <a href="./early-signals.html">Early Signals</a><a href="./technical-journal.html">Technical Trade Journal</a>
    <a href="./recommendations.html">Recommendations</a><a href="./recommendation-analytics.html">Recommendation Analytics</a>
  </div>
  <div class="terminal-sidebar-section">
    <div class="terminal-sidebar-title">QUANT</div>
    <a href="./backtest.html">Backtest All Setup</a><a href="./momentum-dashboard.html">Momentum Dashboard</a>
    <a href="./catalyst-calendar.html">Catalyst Calendar</a>
  </div>
  <div class="terminal-sidebar-section">
    <div class="terminal-sidebar-title">SYSTEM</div>
    <a href="./stock-detail.html">Stock Detail</a><a href="./system-health.html">System Health</a><a href="./admin.html">Admin</a>
  </div>
</aside>"""

COMMAND_CENTER = """<section class="command-center" aria-label="Market Command Center">
  <div class="cc-head">
    <div><span class="cc-kicker">MARKET COMMAND CENTER</span><h1>SPC / QUANT RESEARCH TERMINAL</h1><p>Systematic market monitor — technical breadth, quantitative signals, sector rotation and market intelligence.</p></div>
    <div class="cc-clock"><span id="ccMarketState">MARKET OPEN</span><b id="ccClock">--:-- WIB</b><small id="ccAsOf">AS OF --</small></div>
  </div>
  <div class="cc-regime">
    <div class="cc-metric"><span>MARKET REGIME</span><b id="ccRegime">—</b><small id="ccRegimeSub">Loading breadth</small></div>
    <div class="cc-metric"><span>BREADTH</span><b id="ccBreadth">—</b><small id="ccBreadthSub">—</small></div>
    <div class="cc-metric"><span>QUANT SIGNALS</span><b id="ccSignals">—</b><small id="ccSignalsSub">Bullish / Bearish</small></div>
    <div class="cc-metric"><span>RISK / DISPERSION</span><b id="ccRisk">—</b><small id="ccRiskSub">Score dispersion</small></div>
  </div>
  <div class="cc-grid">
    <section class="cc-panel cc-top-signals"><header><span>TOP QUANT SIGNALS</span><a href="#screener">OPEN SCREENER →</a></header><div id="ccTopSignals" class="cc-list"></div></section>
    <section class="cc-panel"><header><span>SECTOR ROTATION</span><a href="./sector-rotation.html">VIEW →</a></header><div id="ccSectors" class="cc-list"></div></section>
    <section class="cc-panel"><header><span>MARKET INTELLIGENCE</span><a href="./market-intelligence.html">VIEW →</a></header><div id="ccIntel" class="cc-list"></div></section>
  </div>
  <section class="cc-panel cc-monitor" id="screener">
    <header><span>SCREENER / MARKET MONITOR</span><span id="ccMonitorMeta">—</span></header>
    <div class="cc-monitor-grid"><div><span>TOP BULLISH</span><b id="ccBullTickers">—</b></div><div><span>TOP BEARISH</span><b id="ccBearTickers">—</b></div><div><span>STRONGEST CONFLUENCE</span><b id="ccConfTickers">—</b></div></div>
  </section>
</section>"""

COMMAND_JS = r"""
/* ================= terminal command center ================= */
async function renderCommandCenter() {
  const total = ROWS.length;
  const bull = ROWS.filter(r => r.a.score >= 25).length;
  const bear = ROWS.filter(r => r.a.score <= -25).length;
  const neutral = Math.max(total - bull - bear, 0);
  const breadth = total ? (bull - bear) / total * 100 : 0;
  const avg = total ? ROWS.reduce((s, r) => s + r.a.score, 0) / total : 0;
  const dispersion = total ? Math.sqrt(ROWS.reduce((s, r) => s + (r.a.score - avg) ** 2, 0) / total) : 0;
  const regime = breadth >= 20 ? 'BULLISH' : breadth <= -20 ? 'BEARISH' : 'NEUTRAL';
  const risk = dispersion >= 38 ? 'HIGH' : dispersion >= 28 ? 'ELEVATED' : 'CONTROLLED';
  const $c = id => document.getElementById(id);
  if (!$c('ccRegime')) return;
  $c('ccRegime').textContent = regime;
  $c('ccRegime').className = regime === 'BULLISH' ? 'positive' : regime === 'BEARISH' ? 'negative' : 'warning';
  $c('ccRegimeSub').textContent = 'Breadth ' + (breadth >= 0 ? '+' : '') + breadth.toFixed(1) + ' pts';
  $c('ccBreadth').textContent = bull + ' / ' + bear;
  $c('ccBreadthSub').textContent = neutral + ' neutral · ' + total + ' universe';
  $c('ccSignals').textContent = bull;
  $c('ccSignalsSub').textContent = bull + ' bullish · ' + bear + ' bearish';
  $c('ccRisk').textContent = risk;
  $c('ccRiskSub').textContent = 'σ score ' + dispersion.toFixed(1);
  $c('ccAsOf').textContent = 'AS OF ' + (DATA.asof || '—');
  $c('ccMonitorMeta').textContent = total + ' instruments · score engine';

  const topBull = ROWS.filter(r => r.a.score > 0).sort((a,b)=>b.a.score-a.a.score).slice(0,6);
  const topBear = ROWS.filter(r => r.a.score < 0).sort((a,b)=>a.a.score-b.a.score).slice(0,6);
  const topConf = [...ROWS].sort((a,b)=>(b.a.agree/Math.max(b.a.total,1))-(a.a.agree/Math.max(a.a.total,1)) || b.a.score-a.a.score).slice(0,5);
  const row = r => '<div class="cc-row"><b>' + esc(r.s.t) + '</b><span>' + esc(r.s.sec || '—') + '</span><strong class="' + (r.a.score >= 0 ? 'positive':'negative') + '">' + (r.a.score >= 0 ? '+' : '') + r.a.score.toFixed(1) + '</strong><em>' + r.a.agree + '/' + r.a.total + '</em></div>';
  $c('ccTopSignals').innerHTML = topBull.length ? topBull.map(row).join('') : '<div class="cc-empty">No bullish signal above zero.</div>';

  $c('ccBullTickers').textContent = topBull.slice(0,4).map(r=>r.s.t).join(' · ') || '—';
  $c('ccBearTickers').textContent = topBear.slice(0,4).map(r=>r.s.t).join(' · ') || '—';
  $c('ccConfTickers').textContent = topConf.map(r=>r.s.t + ' ' + r.a.agree + '/' + r.a.total).join(' · ') || '—';

  try {
    const [sr, mi] = await Promise.all([
      fetch('data/sector-rotation.json?v='+Date.now(), {cache:'no-store'}).then(x=>x.ok?x.json():null).catch(()=>null),
      fetch('data/market-intelligence.json?v='+Date.now(), {cache:'no-store'}).then(x=>x.ok?x.json():null).catch(()=>null)
    ]);
    if (sr && Array.isArray(sr.sectors)) {
      const sectors = [...sr.sectors].sort((a,b)=>b.avg_score-a.avg_score).slice(0,6);
      $c('ccSectors').innerHTML = sectors.map(s=>'<div class="cc-row"><b>'+esc(s.sector)+'</b><span>'+esc(s.phase || '—')+'</span><strong class="'+(s.avg_score>=0?'positive':'negative')+'">'+(s.avg_score>=0?'+':'')+Number(s.avg_score).toFixed(1)+'</strong><em>'+Number(s.breadth).toFixed(0)+'%</em></div>').join('');
    } else $c('ccSectors').innerHTML='<div class="cc-empty">Sector data unavailable.</div>';
    if (mi && Array.isArray(mi.items)) {
      $c('ccIntel').innerHTML = mi.items.slice(0,5).map(x=>'<div class="cc-row"><b>'+esc(x.ticker)+'</b><span>'+esc(x.market_sentiment || '—')+'</span><strong class="'+(x.score>=25?'positive':'negative')+'">'+(x.score>=0?'+':'')+Number(x.score).toFixed(1)+'</strong><em>'+esc(x.confluence || '—')+'</em></div>').join('');
    } else $c('ccIntel').innerHTML='<div class="cc-empty">Market intelligence unavailable.</div>';
  } catch {}
}
"""

def replace_nav(text):
    pattern = re.compile(r'<nav class="menu-wrap">.*?</nav>', re.S)
    if pattern.search(text):
        return pattern.sub(NAV, text, count=1)
    return text

def inject_index(text):
    text = text.replace('<title>Screener Teknikal Saham IDX — Azharys.hr Capital Markets Desk</title>',
                        '<title>SPC / Quant Research Terminal — Azharys.hr Capital Markets Desk</title>')
    text = text.replace('<section class="hero">', '<section class="hero legacy-hero">', 1)
    text = text.replace('<section class="stats" aria-label="Ringkasan hasil" id="stats">', '<section class="stats legacy-stats" aria-label="Ringkasan hasil" id="stats">', 1)
    if 'class="terminal-sidebar"' not in text:
        text = text.replace('</header>\n  <div id="banner"', '</header>\n  ' + SIDEBAR + '\n  <div id="banner"', 1)
    if 'class="command-center"' not in text:
        text = text.replace('  <section class="hero legacy-hero">', '  ' + COMMAND_CENTER + '\n\n  <section class="hero legacy-hero">', 1)
    marker = '/* ================= init ================= */'
    if COMMAND_JS not in text and marker in text:
        text = text.replace(marker, COMMAND_JS + '\n\n' + marker, 1)
    needle = 'recompute(); render();'
    if 'recompute(); render(); renderCommandCenter();' not in text and needle in text:
        text = text.replace(needle, 'recompute(); render(); renderCommandCenter();', 1)
    return text

changed = 0
for path in sorted(ROOT.glob("*.html")):
    text = path.read_text(encoding="utf-8")
    before = text
    if LINK not in text and "</head>" in text:
        text = text.replace("</head>", f"{LINK}\n</head>", 1)
    text = replace_nav(text)
    if path.name == "index.html":
        text = inject_index(text)
    if text != before:
        path.write_text(text, encoding="utf-8")
        changed += 1

print(f"Quant Research Terminal shell prepared on {changed} HTML pages.")
