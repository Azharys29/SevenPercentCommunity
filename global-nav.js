(()=>{'use strict';
const groups=[
{title:'Overview & Intelligence',items:[
['Market Overview','index.html','Ringkasan terminal dan akses seluruh modul'],
['Equity Intelligence Graph','equity-intelligence-graph.html','Transmisi ekonomi, valuasi, dan tesis'],
['Catalyst Transmission Map','catalyst-transmission-map.html','Peta transmisi katalis, bukti, dan kontra-bukti'],
['Investment Decision Engine','investment-decision-engine.html','Tesis, valuasi, katalis, dan risiko'],
['Market Intelligence','market-intelligence.html','Kondisi pasar dan confluence'],
['Market Activity','market-activity.html','Aktivitas dan ringkasan perdagangan'],
['Market Catalyst','market-catalyst.html','Katalis pasar dan faktor penggerak'],
['Catalyst Calendar','catalyst-calendar.html','Kalender katalis dan peristiwa'],
['AI Research Pack','ai-research-pack.html','Ekspor snapshot untuk riset web'],
['Weekly Quant Report','weekly-quant-report.html','Laporan kuantitatif berkala'],
]},
{title:'Fundamental & Valuation',items:[
['Fundamental','fundamental.html','Analisis fundamental emiten'],
['Value Gap','value-gap.html','PER historis dan gap valuasi'],
['Dividend Intelligence','dividend-intelligence.html','Analisis dividen dan estimasi yield'],
['Equity Research Builder','research-report.html','Menyusun laporan riset emiten'],
]},
{title:'Sector, Macro & Market Structure',items:[
['Sector Rotation','sector-rotation.html','Rotasi dan kekuatan sektor'],
['Commodity Play','commodity-play.html','Paparan saham terhadap komoditas'],
['Heatmap','heatmap.html','Peta visual pasar'],
['Relative Strength','relative-strength.html','Kekuatan relatif saham'],
['Volume Intelligence','volume-intelligence.html','Analisis aktivitas volume']]},
{title:'Signals & Trading Tools',items:[
['Teknikal','teknikal.html','Analisis teknikal'],
['Early Signals','early-signals.html','Sinyal awal'],
['Momentum Dashboard','momentum-dashboard.html','Momentum lintas saham'],
['Markov Momentum Fusion','markov-momentum-fusion.html','Regime Markov + MACD/RSI dan uji strategi'],
['Signal Intelligence','signal-intelligence.html','Rangkuman intelijen sinyal'],
['New Bullish','new-bullish.html','Daftar saham bullish terbaru'],
['OU Mean Reversion','ou-mean-reversion.html','Analisis mean reversion'],
['Stock Detail','stock-detail.html','Detail saham'],
['Recommendations','recommendations.html','Rekomendasi aktif'],
['Recommendation Analytics','recommendation-analytics.html','Analitik rekomendasi'],
['Recommendation Report','recommendation-report.html','Laporan rekomendasi'],
['Technical Trade Journal','technical-journal.html','Jurnal perdagangan teknikal'],
['Backtest','backtest.html','Pengujian strategi historis']]},
{title:'Administration & System',items:[
['System Health','system-health.html','Kesehatan data dan sistem'],
['Research Manual','research-manual.html','Panduan metodologi terminal'],
['Admin','admin.html','Pengaturan administratif'],
['AI Insights','ai-insights.html','Insight berbantuan AI'],
['Gemini AI Research','market-intelligence.html','Buka panel analisis Gemini'],
['AI Login','ai-login.html','Masuk atau buat akun AI'],
['AI Settings','ai-settings.html','Atur menu yang menggunakan Gemini']]}
];
const current=decodeURI(location.pathname.split('/').pop()||'index.html');
// Cache-bust shared navigation after menu updates so GitHub Pages/mobile browsers do not keep an older menu script.

const all=groups.flatMap(g=>g.items);
const fontLink=document.createElement('link');fontLink.rel='stylesheet';fontLink.href='https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap';document.head.appendChild(fontLink);
const style=document.createElement('style');style.textContent=`
#spcNavButton{position:fixed;z-index:10001;top:12px;right:14px;display:flex;align-items:center;gap:9px;border:1px solid #45627f;background:rgba(12,20,31,.97);color:#f3f6fa;padding:10px 13px;border-radius:7px;font:600 13px/1.2 system-ui,sans-serif;box-shadow:0 5px 22px #0008;cursor:pointer}
#spcNavButton .spcHamb{font-size:18px;color:#add6ff}
#spcNavShade{position:fixed;inset:0;background:rgba(1,5,10,.72);z-index:10002;opacity:0;visibility:hidden;transition:opacity .18s}
#spcNavShade.open{opacity:1;visibility:visible}
#spcNavDrawer{position:absolute;top:0;right:0;height:100%;width:min(430px,94vw);background:#0b121d;border-left:1px solid #304966;box-shadow:-18px 0 45px #0008;display:flex;flex-direction:column;transform:translateX(100%);transition:transform .22s ease}
#spcNavShade.open #spcNavDrawer{transform:translateX(0)}
.spcNavHead{padding:20px 18px 14px;border-bottom:1px solid #25394f;display:flex;align-items:center;justify-content:space-between;gap:12px}
.spcNavBrand{font:600 11px/1.4 ui-monospace,monospace;letter-spacing:.14em;color:#add6ff}.spcNavHead strong{display:block;font:500 23px/1.25 Georgia,serif;color:#f2ebdd;margin-top:5px}
#spcNavClose{background:#152235;color:#eaf3ff;border:1px solid #304966;border-radius:5px;font-size:20px;padding:4px 11px;cursor:pointer}
.spcNavSearch{padding:12px 16px;border-bottom:1px solid #25394f}.spcNavSearch input{width:100%;box-sizing:border-box;background:#080e16!important;color:#f3f6fa!important;border:1px solid #304966!important;border-radius:6px;padding:11px 12px;font:14px system-ui,sans-serif}
#spcNavList{overflow:auto;padding:6px 12px 24px;overscroll-behavior:contain}
.spcNavGroup{margin:12px 0 16px}.spcNavGroupTitle{font:600 10px ui-monospace,monospace;letter-spacing:.12em;text-transform:uppercase;color:#7fa3cb;padding:0 8px 7px}
.spcNavLink{display:block;color:#b9c7d7!important;text-decoration:none!important;padding:10px 10px;border-radius:5px;border:1px solid transparent;font:14px/1.3 system-ui,sans-serif}
.spcNavLink:hover,.spcNavLink:focus-visible{background:#142236;border-color:#304966;color:#fff!important}
.spcNavLink.active{background:#152a40;border-color:#45627f;color:#add6ff!important}
.spcNavLink small{display:block;font-size:11px;color:#7f91a6;margin-top:4px}
#spcNavEmpty{display:none;padding:20px;color:#a3adbc;font-size:13px}
#spcModuleHub{margin:18px 0 26px;padding:20px;border:1px solid #304966;background:linear-gradient(135deg,rgba(17,30,46,.98),rgba(9,15,24,.98));border-radius:8px}
#spcModuleHub h2{margin:0;color:#f2ebdd;font:500 clamp(23px,3vw,30px)/1.2 Georgia,serif}
#spcModuleHub>p{margin:7px 0 18px;color:#a3adbc;font-size:14px;max-width:75ch}
.spcHubGroup{margin:18px 0 0}.spcHubGroup h3{font:600 10px ui-monospace,monospace;letter-spacing:.12em;text-transform:uppercase;color:#7fa3cb;margin:0 0 9px}
.spcHubGrid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}
.spcHubCard{display:block;text-decoration:none!important;color:#f3f6fa!important;background:#0c1521;border:1px solid #263b51;border-radius:6px;padding:12px;min-height:74px}
.spcHubCard:hover{border-color:#85b7eb;background:#142236}.spcHubCard strong{display:block;font-size:13px;font-weight:600}.spcHubCard span{display:block;color:#91a1b4;font-size:11px;line-height:1.4;margin-top:5px}
@media(max-width:800px){.spcHubGrid{grid-template-columns:repeat(2,minmax(0,1fr))}#spcNavButton{top:8px;right:8px;padding:9px 10px}.spcNavHead{padding-top:58px}}
@media(max-width:420px){.spcHubGrid{grid-template-columns:1fr 1fr}.spcHubCard{padding:10px 8px}}
.top{padding-right:145px!important}
@media(max-width:800px){.top{padding-right:0!important;padding-top:58px!important}}
#spcSideNav{position:fixed;z-index:9998;left:0;top:0;bottom:0;width:218px;box-sizing:border-box;background:#0b121d;border-right:1px solid #263b51;display:flex;flex-direction:column;color:#dbe7f5;font-family:system-ui,sans-serif}
.spcSideBrand{padding:19px 15px 14px;border-bottom:1px solid #25394f;font:700 11px/1.7 ui-monospace,monospace;letter-spacing:.12em;color:#add6ff}.spcSideBrand span{color:#7f91a6;font-weight:500}
.spcSideSearch{padding:10px;border-bottom:1px solid #25394f}.spcSideSearch input{width:100%;box-sizing:border-box;background:#080e16;color:#f3f6fa;border:1px solid #304966;border-radius:5px;padding:9px;font:12px system-ui,sans-serif}
#spcSideLinks{overflow:auto;padding:4px 9px 20px}.spcSideGroup{margin:12px 0}.spcSideGroupTitle{padding:0 7px 5px;color:#7fa3cb;font:600 9px/1.4 ui-monospace,monospace;letter-spacing:.08em;text-transform:uppercase}
.spcSideLink{display:block;padding:7px;border-radius:4px;color:#b9c7d7!important;text-decoration:none!important;font:12px/1.3 system-ui,sans-serif;border:1px solid transparent}.spcSideLink:hover{background:#142236;color:#fff!important}.spcSideLink.active{background:#152a40;border-color:#45627f;color:#add6ff!important}
body{padding-left:218px!important;box-sizing:border-box}
@media(max-width:1000px){#spcSideNav{display:none}body{padding-left:0!important}}
\nbody{font-family:Inter,system-ui,-apple-system,'Segoe UI',sans-serif!important}\nbutton,input,select,textarea{font-family:Inter,system-ui,sans-serif}\n.spcNavGroupTitle,.spcSideGroupTitle,.spcNavBrand,.spcSideBrand{font-family:'IBM Plex Mono',ui-monospace,monospace}\nbody.spcNavOpen{overflow:hidden}
.menu-wrap,details.menu{display:none!important}
`;document.head.appendChild(style);
const btn=document.createElement('button');btn.id='spcNavButton';btn.type='button';btn.setAttribute('aria-label','Buka semua menu terminal');btn.innerHTML='<span class="spcHamb">☰</span><span>Semua Menu</span>';document.body.appendChild(btn);
const shade=document.createElement('div');shade.id='spcNavShade';shade.innerHTML='<aside id="spcNavDrawer" role="dialog" aria-modal="true" aria-label="Navigasi terminal"><div class="spcNavHead"><div><div class="spcNavBrand">SEVENPERCENTCOMMUNITY</div><strong>Terminal Navigator</strong></div><button id="spcNavClose" type="button" aria-label="Tutup menu">×</button></div><div class="spcNavSearch"><input id="spcNavQuery" type="search" placeholder="Cari menu atau fitur…" autocomplete="off"></div><div id="spcNavList"></div><div id="spcNavEmpty">Tidak ada menu yang cocok.</div></aside>';document.body.appendChild(shade);
const list=shade.querySelector('#spcNavList'),query=shade.querySelector('#spcNavQuery'),empty=shade.querySelector('#spcNavEmpty');
function makeLink(item){const a=document.createElement('a');a.className='spcNavLink'+(item[1].split('#')[0]===current?' active':'');a.href='./'+item[1];a.innerHTML='<span>'+item[0]+'</span><small>'+item[2]+'</small>';return a}
function render(filter=''){list.innerHTML='';let count=0;groups.forEach(g=>{const matches=g.items.filter(i=>(i[0]+' '+i[1]+' '+i[2]+' '+g.title).toLowerCase().includes(filter.toLowerCase()));if(!matches.length)return;count+=matches.length;const section=document.createElement('section');section.className='spcNavGroup';const h=document.createElement('div');h.className='spcNavGroupTitle';h.textContent=g.title;section.appendChild(h);matches.forEach(i=>section.appendChild(makeLink(i)));list.appendChild(section)});empty.style.display=count?'none':'block'}
function open(){shade.classList.add('open');document.body.classList.add('spcNavOpen');btn.setAttribute('aria-expanded','true');setTimeout(()=>query.focus(),80)}
function close(){shade.classList.remove('open');document.body.classList.remove('spcNavOpen');btn.setAttribute('aria-expanded','false');btn.focus()}
btn.setAttribute('aria-expanded','false');btn.addEventListener('click',open);shade.querySelector('#spcNavClose').addEventListener('click',close);shade.addEventListener('click',e=>{if(e.target===shade)close()});document.addEventListener('keydown',e=>{if(e.key==='Escape'&&shade.classList.contains('open'))close()});query.addEventListener('input',()=>render(query.value.trim()));render();
// Persistent left navigation on desktop. The same complete menu remains available in the burger drawer.
const side=document.createElement('nav');side.id='spcSideNav';side.setAttribute('aria-label','Semua modul terminal');
side.innerHTML='<div class="spcSideBrand">SEVENPERCENT<br><span>TERMINAL MENU</span></div><div class="spcSideSearch"><input id="spcSideQuery" type="search" placeholder="Cari modul…" aria-label="Cari modul"></div><div id="spcSideLinks"></div>';
document.body.appendChild(side);
const sideLinks=side.querySelector('#spcSideLinks'),sideQuery=side.querySelector('#spcSideQuery');
function renderSide(filter=''){sideLinks.innerHTML='';let count=0;groups.forEach(g=>{const matches=g.items.filter(i=>(i[0]+' '+i[1]+' '+i[2]+' '+g.title).toLowerCase().includes(filter.toLowerCase()));if(!matches.length)return;count+=matches.length;const section=document.createElement('section');section.className='spcSideGroup';const h=document.createElement('div');h.className='spcSideGroupTitle';h.textContent=g.title;section.appendChild(h);matches.forEach(i=>{const a=document.createElement('a');a.className='spcSideLink'+(i[1].split('#')[0]===current?' active':'');a.href='./'+i[1];a.textContent=i[0];section.appendChild(a)});sideLinks.appendChild(section)});sideLinks.dataset.count=String(count)}
sideQuery.addEventListener('input',()=>renderSide(sideQuery.value.trim()));renderSide();

/* Terminal appearance switch — positioned immediately left of the burger menu. */
const themeStyle=document.createElement('style');
themeStyle.textContent=`
#spcThemeToggle{position:fixed;z-index:10001;top:12px;right:154px;display:flex;align-items:center;gap:7px;border:1px solid #45627f;background:#101c2c;color:#f3f7fc;padding:10px 12px;border-radius:7px;font:600 12px/1.2 Inter,system-ui,sans-serif;cursor:pointer;box-shadow:0 5px 22px #0002;white-space:nowrap}
#spcThemeToggle .spcThemeIcon{font-size:15px}
html[data-spc-theme="light"] #spcThemeToggle{background:linear-gradient(135deg,#fff7ed,#eff6ff);color:#26334a;border-color:#b9c9e4}
html[data-spc-theme="light"] #spcNavButton{background:linear-gradient(135deg,#e0f2fe,#ede9fe);color:#26334a;border-color:#a5b4fc}
html[data-spc-theme="light"] #spcNavShade{background:rgba(51,65,85,.45)}
html[data-spc-theme="light"] #spcNavDrawer,html[data-spc-theme="light"] #spcSideNav{background:linear-gradient(180deg,#f8fbff,#f4f0ff)!important;color:#1e293b!important;border-color:#cbd5e1!important}
html[data-spc-theme="light"] .spcNavHead,html[data-spc-theme="light"] .spcSideBrand{border-color:#dbeafe!important}
html[data-spc-theme="light"] .spcNavBrand,html[data-spc-theme="light"] .spcSideBrand{color:#4338ca!important}
html[data-spc-theme="light"] .spcNavLink,html[data-spc-theme="light"] .spcSideLink{color:#334155!important}
html[data-spc-theme="light"] .spcNavLink:hover,html[data-spc-theme="light"] .spcSideLink:hover{background:linear-gradient(90deg,#dbeafe,#ede9fe)!important;color:#3730a3!important;border-color:#c4b5fd!important}
html[data-spc-theme="light"] .spcNavLink.active,html[data-spc-theme="light"] .spcSideLink.active{background:linear-gradient(90deg,#bfdbfe,#ddd6fe)!important;color:#312e81!important;border-color:#a5b4fc!important}
html[data-spc-theme="light"] .spcNavGroupTitle,html[data-spc-theme="light"] .spcSideGroupTitle{color:#6d28d9!important}
html[data-spc-theme="light"] #spcNavQuery,html[data-spc-theme="light"] #spcSideQuery{background:#fff!important;color:#1e293b!important;border-color:#c7d2fe!important}
@media(max-width:520px){#spcThemeToggle{right:132px;top:12px;padding:9px 10px}#spcThemeToggle .spcThemeLabel{display:none}}
`;
document.head.appendChild(themeStyle);
const themeButton=document.createElement('button');
themeButton.id='spcThemeToggle';themeButton.type='button';
themeButton.innerHTML='<span class="spcThemeIcon" aria-hidden="true">☀</span><span class="spcThemeLabel">Light mode</span>';
themeButton.setAttribute('aria-label','Ganti mode tampilan');themeButton.setAttribute('aria-pressed','false');
document.body.appendChild(themeButton);
function applyTheme(theme){
 const light=theme==='light';
 document.documentElement.dataset.spcTheme=light?'light':'dark';
 document.documentElement.style.colorScheme=light?'light':'dark';
 themeButton.innerHTML='<span class="spcThemeIcon" aria-hidden="true">'+(light?'☾':'☀')+'</span><span class="spcThemeLabel">'+(light?'Dark mode':'Light mode')+'</span>';
 themeButton.setAttribute('aria-pressed',String(light));
 try{localStorage.setItem('spc-terminal-theme',light?'light':'dark')}catch(e){}
}
let savedTheme='dark';try{savedTheme=localStorage.getItem('spc-terminal-theme')||'dark'}catch(e){}
applyTheme(savedTheme);
themeButton.addEventListener('click',()=>applyTheme(document.documentElement.dataset.spcTheme==='light'?'dark':'light'));
if(current!=='ai-settings'){const aiScript=document.createElement('script');aiScript.src='./ai-assistant.js?v=20261023-gemini-nav-fix-1';document.head.appendChild(aiScript);}
if(current==='index.html'){const hub=document.getElementById('spcModuleHub');if(hub)hub.remove();}
})();