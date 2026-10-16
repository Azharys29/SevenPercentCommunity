(()=>{'use strict';
const groups=[
{title:'Overview & Intelligence',items:[
['Market Overview','index.html','Ringkasan terminal dan akses seluruh modul'],
['Equity Intelligence Graph','equity-intelligence-graph.html','Transmisi ekonomi, valuasi, dan tesis'],
['Market Intelligence','market-intelligence.html','Kondisi pasar dan confluence'],
['Market Activity','market-activity.html','Aktivitas dan ringkasan perdagangan'],
['Market Catalyst','market-catalyst.html','Katalis pasar dan faktor penggerak'],
['Catalyst Calendar','catalyst-calendar.html','Kalender katalis dan peristiwa'],
['AI Research Pack','ai-research-pack.html','Ekspor snapshot untuk riset web'],
['Weekly Quant Report','weekly-quant-report.html','Laporan kuantitatif berkala']]},
{title:'Fundamental & Valuation',items:[
['Fundamental','fundamental.html','Analisis fundamental emiten'],
['Value Gap','value-gap.html','PER historis dan gap valuasi'],
['Dividend Intelligence','dividend-intelligence.html','Analisis dividen dan estimasi yield'],
['Equity Research Builder','research-report.html','Menyusun laporan riset emiten'],
['Earnings Quality','fundamental.html#quality','Kembali ke modul fundamental']]},
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
['AI Insights','ai-insights.html','Insight berbantuan AI']]}
];
const current=decodeURI(location.pathname.split('/').pop()||'index.html');
const all=groups.flatMap(g=>g.items);
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
body.spcNavOpen{overflow:hidden}
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
if(current==='index.html'){
const header=document.querySelector('.top,header.top,header');
if(header){const hub=document.createElement('section');hub.id='spcModuleHub';hub.innerHTML='<h2>Semua Modul Terminal</h2><p>Akses seluruh fitur dari satu tempat. Gunakan pencarian pada tombol “Semua Menu” untuk berpindah modul tanpa kembali ke halaman utama.</p>';
groups.forEach(g=>{const sec=document.createElement('section');sec.className='spcHubGroup';const h=document.createElement('h3');h.textContent=g.title;sec.appendChild(h);const grid=document.createElement('div');grid.className='spcHubGrid';g.items.forEach(i=>{const a=document.createElement('a');a.className='spcHubCard';a.href='./'+i[1];a.innerHTML='<strong>'+i[0]+'</strong><span>'+i[2]+'</span>';grid.appendChild(a)});sec.appendChild(grid);hub.appendChild(sec)});header.insertAdjacentElement('afterend',hub)}
}
})();