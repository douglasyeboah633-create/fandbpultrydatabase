let U = guard('manager');
document.getElementById('who').textContent = U?U.full_name:'';
document.getElementById('shdate').value = new Date().toISOString().slice(0,10);
let PEND = {}, ARCHROWS = [], DAYROWS = [], RECS = [], FARM = null, DAYDATE = '';
const SECTIONS = ['dash','shift','archive','records','workers'];
function show(id){
 SECTIONS.forEach(x=>{const e=document.getElementById(x); if(e) e.style.display=x===id?'block':'none';});
 const i=SECTIONS.indexOf(id);
 document.querySelectorAll('#side a').forEach(function(a,n){ a.classList.toggle('on', n===i); });
 document.getElementById('side').classList.remove('open');
 window.scrollTo(0,0);
 if(id==='records') loadRecs();
 if(id==='dash') loadDash();
}
function v(id){ return document.getElementById(id).value; }
function shiftName(r){ const s=(r.shift||'daily'); const key=s.toLowerCase(); const emo={daily:'📋',morning:'🌅',afternoon:'☀️',evening:'🌙'}[key]||'📋'; const lab=(key==='daily')?'Daily (whole day)':s.charAt(0).toUpperCase()+s.slice(1); return emo+' '+lab; }
function imgT(url){ return url?(url+(url.indexOf('?')>-1?'&':'?')+'token='+tok()):''; }
function rMoney(r){ const a=(r.amount||0); return a>0?money(a):money(r.sales_total||0); }
function tdet(r, arch){
 return '<div class="panel">'+
 '<p>'+(r.seen_by_manager?'<span class="badge appr">✅ reviewed — kept in Archive</span>':'<span class="badge pend">not checked yet</span>')+'</p>'+
 (r.death_image?('<div style="margin-bottom:8px"><b>📷 Mortality photo:</b> <small>(click to see it big)</small><br><img src="'+imgT(r.death_image)+'" style="max-width:260px;border-radius:8px;margin-top:4px;cursor:zoom-in" onclick="viewImg(this.src)"></div>'):'')+
 (r.birds_died||r.death_reason?('<p>☠️ Mortality: '+(r.birds_died||0)+' died'+(r.death_reason?(' — '+r.death_reason):'')+'</p>'):'')+
 (r.amount||r.sales_total?('<p>💰 Amount received: <b>'+rMoney(r)+'</b></p>'):'')+
 (r.problems?('<p style="background:#fef2f2;padding:6px;border-radius:6px">⚠️ Problems: '+r.problems+'</p>'):'')+
 (r.notes?('<p>📝 Notes: '+r.notes+'</p>'):'')+
 (r.sales_summary?('<p>🧾 Sales lines: '+r.sales_summary+'</p>'):'')+
 (r.manager_comment?('<p style="background:#ecfdf5;padding:6px;border-radius:6px"><b>💬 Your comment:</b> '+r.manager_comment+'</p>'):'')+
 '<div class="row" style="margin-top:8px">'+(r.seen_by_manager?'':'<button class="btn btn-g" onclick="reviewR('+r.id+')">✅ Reviewed — move to Archive</button>')+
 '<input id="cmt'+r.id+'" placeholder="Write a comment for the worker..." style="max-width:240px">'+
 '<button class="btn btn-o" onclick="commentR('+r.id+')">💬 Send comment</button>'+
 '<button class="btn btn-r" onclick="delR('+r.id+')">🗑 Delete</button></div></div>';
}
function trow(r, arch){
 const cols = arch?12:11;
 return '<tr id="rrow'+r.id+'">'+
 '<td>'+shiftName(r)+'</td>'+
 (arch?'<td>'+(r.date||'')+'</td>':'')+
 '<td>'+r.worker_name+'</td>'+
 '<td>'+(r.feed_done?('✅ '+(r.feed_bags||0)+' bags / '+(r.feed_kg||0)+' kg<br><small>'+(r.birds_fed||0)+' birds'+(r.feed_qty?' · '+r.feed_qty:'')+'</small>'):'—')+'</td>'+
 '<td>'+(r.water_done?('✅ '+(r.water_liters||0)+' L'):'—')+'</td>'+
 '<td>'+(r.eggs_collected||0)+'<br><small>'+(r.eggs_broken||0)+' broken</small></td>'+
 '<td>'+(r.egg_crates||0)+' packed<br><small>'+(r.crates_sold||0)+' sold</small></td>'+
 '<td>'+(r.chickens_sold||0)+'</td>'+
 '<td>'+(r.birds_died||0)+(r.death_reason?('<br><small>'+r.death_reason+'</small>'):'')+'</td>'+
 '<td>'+(r.death_image?('<img src="'+imgT(r.death_image)+'" style="max-width:70px;border-radius:6px;cursor:zoom-in" title="Click to see the photo big" onclick="viewImg(this.src)">'):'—')+'</td>'+
 '<td><b>'+rMoney(r)+'</b>'+(r.sales_summary?('<br><small>'+r.sales_summary+'</small>'):'')+'</td>'+
 '<td><button class="btn btn-o" onclick="expandR('+r.id+')">👁 Details</button></td>'+
 '</tr>'+
 '<tr id="rdet'+r.id+'" style="display:none"><td colspan="'+cols+'">'+tdet(r,arch)+'</td></tr>';
}
function tbl(rows, arch){
 let h='<div class="twrap"><table><thead><tr><th>Report</th>'+(arch?'<th>Date</th>':'')+'<th>Worker</th><th>🍽️ Feed</th><th>💧 Water</th><th>🥚 Eggs</th><th>📦 Crates</th><th>🐔 Chickens sold</th><th>☠️ Died</th><th>📷 Photo</th><th>💰 Amount</th><th>Actions</th></tr></thead><tbody>';
 h += rows.length?rows.map(function(r){return trow(r,arch);}).join(''):('<tr><td colspan="'+(arch?12:11)+'">None.</td></tr>');
 return h+'</tbody></table></div>';
}
async function loadShift(){
 try{
  const d=v('shdate');
  const rows=await api('/api/shift-reports?date='+d);
  DAYROWS=rows; DAYDATE=d;
  const who=rows.map(r=>r.worker_name||'a worker');
  document.getElementById('shcov').innerHTML=rows.length?
   ('✅ '+rows.length+' daily report(s) received for '+d+' — '+who.join(', ')):
   '⏳ No report has been sent for '+d+' yet.';
  const T=k=>rows.reduce((a,r)=>a+(r[k]||0),0);
  document.getElementById('shtot').innerHTML='<small>🍽️ '+T('feed_bags')+' bags / '+T('feed_kg')+' kg feed · 💧 '+T('water_liters')+' L water · 🥚 '+T('eggs_collected')+' eggs ('+T('egg_crates')+' crates packed, '+T('crates_sold')+' sold) · 🐔 '+T('chickens_sold')+' chickens sold · ☠️ '+T('birds_died')+' died · 💰 '+money(rows.reduce((a,r)=>a+((r.amount||0)||(r.sales_total||0)),0))+'</small>';
  PEND={};
  const pend=rows.filter(r=>!r.seen_by_manager);
  pend.forEach(r=>PEND[r.id]=1);
  document.getElementById('shlist').innerHTML='<h2>📋 Reports for '+d+' — '+pend.length+' waiting to be checked</h2>'+(pend.length?tbl(pend,false):'<div class="panel">✅ All reports for this day have been checked. They are kept in the 📚 Report Archive for future reference.</div>');
 }catch(e){ document.getElementById('shlist').innerHTML='<div class="panel">⚠️ Could not load reports: '+e.message+' — try the Load day button.</div>'; }
}
async function expandR(id){
 const det=document.getElementById('rdet'+id);
 if(!det) return;
 const open=(det.style.display==='none');
 det.style.display=open?'':'none';
 if(open&&PEND[id]){
  delete PEND[id];
  try{ await api('/api/shift-reports/'+id+'/reviewed',{method:'POST'}); say('#m',true,'Report checked — moved to 📚 Report Archive.'); }catch(e){}
  loadShift(); loadArchive();
 }
}
async function reviewR(id){ try{ const j=await api('/api/shift-reports/'+id+'/reviewed',{method:'POST'}); say('#m',true,j.message); loadShift(); loadArchive(); }catch(e){ say('#m',false,e.message); } }
async function commentR(id){ const c=document.getElementById('cmt'+id).value; if(!c){ say('#m',false,'Write the comment first.'); return; } try{ await api('/api/shift-reports/'+id+'/comment',{method:'POST',body:{comment:c}}); say('#m',true,'Comment sent to worker.'); loadShift(); }catch(e){ say('#m',false,e.message); } }
async function loadArchive(){
 try{ ARCHROWS=await api('/api/shift-reports?status=reviewed'); }
 catch(e){ ARCHROWS=[]; document.getElementById('arclist').innerHTML='<div class="panel">⚠️ Could not load archive: '+e.message+' — try 🔍 Search.</div>'; return; }
 renderArchive();
}
function filteredArchive(){
 const q=(v('arcq')||'').trim().toLowerCase();
 const d=v('arcdate');
 let rows=ARCHROWS.slice();
 if(q){ rows=rows.filter(function(r){ return ((r.worker_name||'')+' '+(r.shift||'')+' '+(r.date||'')+' '+(r.death_reason||'')+' '+(r.notes||'')+' '+(r.problems||'')+' '+(r.sales_summary||'')).toLowerCase().indexOf(q)>-1; }); }
 if(d){ rows=rows.filter(function(r){ return r.date===d; }); }
 return rows;
}
function renderArchive(){
 const q=(v('arcq')||'').trim().toLowerCase();
 const d=v('arcdate');
 const rows=filteredArchive();
 const tot=rows.reduce((a,r)=>a+((r.amount||0)||(r.sales_total||0)),0);
 document.getElementById('arclist').innerHTML='<h3>📚 '+rows.length+' report(s)'+(q?(' matching "'+q+'"'):'')+(d?(' for '+d):'')+' — 💰 total '+money(tot)+'</h3>'+(rows.length?tbl(rows,true):'<div class="panel">No reports found. '+(q?'Try another search word. ':'')+'Open a report on the 🌅 Worker Reports page — it will move here automatically.</div>');
}
async function searchArchive(){ await loadArchive(); }
async function expWeeklyCSV(){
 try{
  const w=await api('/api/shift-reports/weekly');
  toCSV(w.days.map(function(d,i){return {date:d,feed_bags:w.feeding_bags[i]||0,feed_kg:w.feeding_kg[i]||0,water_litres:w.water_liters[i]||0,eggs_collected:w.eggs[i]||0,egg_crates:w.egg_crates[i]||0,chickens_sold:w.chickens_sold[i]||0,amount:(w.amounts&&w.amounts[i])||0};}),'weekly_report.csv');
 }catch(e){ say('#m',false,e.message); }
}
async function expArchiveCSV(){
 let rows=ARCHROWS.length?ARCHROWS.slice():[];
 try{ if(!rows.length) rows=await api('/api/shift-reports?status=reviewed'); }catch(e){}
 const q=(v('arcq')||'').trim().toLowerCase();
 if(q){ rows=rows.filter(function(r){ return ((r.worker_name||'')+' '+(r.shift||'')+' '+(r.date||'')).toLowerCase().indexOf(q)>-1; }); }
 toCSV(rows.map(function(r){return {date:r.date,shift:r.shift,worker:r.worker_name,feed_bags:r.feed_bags||0,feed_kg:r.feed_kg||0,birds_fed:r.birds_fed||0,water_liters:r.water_liters||0,eggs_collected:r.eggs_collected||0,eggs_broken:r.eggs_broken||0,crates_packed:r.egg_crates||0,crates_sold:r.crates_sold||0,chickens_sold:r.chickens_sold||0,birds_died:r.birds_died||0,death_reason:r.death_reason||'',amount:r.amount||r.sales_total||0,problems:r.problems||'',notes:r.notes||''};}),'report_archive.csv');
}
async function loadWorkers(){
 try{
  const ws=await api('/api/workers');
  document.getElementById('wlist').innerHTML='<div class="twrap"><table><thead><tr><th>Name</th><th>Username</th><th>Status</th><th>Actions</th></tr></thead><tbody>'+
   ws.map(w=>'<tr><td>'+w.full_name+'</td><td>'+w.username+'</td><td>'+badge(w.status==='disabled'?'rejected':'approved')+'</td><td class="row"><button class="btn btn-o" onclick="disW('+w.id+')">'+(w.status==='active'?'Disable':'Enable')+'</button><button class="btn btn-o" onclick="resetW('+w.id+')">Reset Password</button><button class="btn btn-r" onclick="delW('+w.id+')">Delete</button></td></tr>').join('')+'</tbody></table></div>';
 }catch(e){ document.getElementById('wlist').innerHTML='<div class="panel">⚠️ Could not load workers: '+e.message+'</div>'; }
}
async function addW(e){ e.preventDefault(); try{ const j=await api('/api/workers',{method:'POST',body:{full_name:v('wn'),username:v('wu'),email:v('we'),password:v('wp')}}); say('#m',true,j.message); loadWorkers(); }catch(err){ say('#m',false,err.message); } }
async function disW(id){ try{ const all=await api('/api/workers'); const u=all.find(x=>x.id===id); await api('/api/workers/'+id,{method:'PUT',body:{status:u.status==='active'?'disabled':'active'}}); loadWorkers(); }catch(e){ say('#m',false,e.message); } }
async function resetW(id){ const p=prompt('Type a NEW password for this worker:',''); if(!p) return; try{ await api('/api/workers/'+id+'/reset-password',{method:'POST',body:{password:p}}); say('#m',true,'Password reset.'); }catch(e){ say('#m',false,e.message); } }
async function delW(id){ if(!confirm('Delete worker?')) return; try{ await api('/api/workers/'+id,{method:'DELETE'}); loadWorkers(); }catch(e){ say('#m',false,e.message); } }
async function delR(id){ if(!confirm('Delete this report?')) return; try{ await api('/api/shift-reports/'+id,{method:'DELETE'}); say('#m',true,'Report deleted.'); loadShift(); loadArchive(); }catch(e){ say('#m',false,e.message); } }
/* ================= DASHBOARD ================= */
function fmtNum(n){ return Number(n||0).toLocaleString(); }
function niceDate(d){ try{ return new Date(d+'T00:00:00').toLocaleDateString(undefined,{weekday:'long',day:'numeric',month:'long',year:'numeric'}); }catch(e){ return d||''; } }
function barChart(elId, series, key, bad){
 const el=document.getElementById(elId);
 if(!el) return;
 const vals=series.map(s=>Number(s[key]||0));
 const max=Math.max.apply(null, vals.concat([1]));
 el.innerHTML=series.map(function(s,i){
  const val=vals[i];
  const h=val>0?Math.max(5, Math.round(val/max*100)):2;
  const cls='bar'+(val>0?(bad?' bad':''):' zero');
  const label=s.date+': '+(key==='amount'?money(val):fmtNum(val));
  return '<div class="'+cls+'" style="height:'+h+'%" title="'+label+'"></div>';
 }).join('');
 const wrap=el.parentNode;
 let lab=wrap.querySelector('.cmplab');
 if(!lab){ lab=document.createElement('div'); lab.className='cmplab'; wrap.appendChild(lab); }
 lab.innerHTML='<span>'+series[0].date.slice(5)+'</span><span>today ('+series[series.length-1].date.slice(5)+')</span>';
}
function fmtCmp(val, kind){ return kind==='money'?money(val):fmtNum(val); }
function diffTag(a, b, goodWhenUp){
 if(!b) return a?'<span class="up">first activity</span>':'<span class="same">—</span>';
 const pct=Math.round((a-b)/b*100);
 if(pct===0) return '<span class="same">no change</span>';
 const up=pct>0, good=goodWhenUp?up:!up;
 return '<span class="'+(good?'up':'down')+'">'+(up?'▲ +':'▼ −')+Math.abs(pct)+'%</span>';
}
const CMP_ROWS=[
 ['💰 Amount received','amount','money'],
 ['🥚 Eggs collected','eggs_collected','num'],
 ['📦 Egg crates packed','egg_crates','num'],
 ['🐔 Chickens sold','chickens_sold','num'],
 ['☠️ Birds died','birds_died','num'],
 ['🍽️ Feed used (bags)','feed_bags','num'],
 ['💧 Water given (litres)','water_liters','num'],
 ['📋 Reports received','reports','num']
];
function renderCmp(F){
 const a=F.month.totals||{}, b=F.last_month.totals||{};
 document.getElementById('cmpTitle').textContent='📆 '+F.month.label+' vs '+F.last_month.label;
 let h='<div class="twrap"><table><thead><tr><th>What</th><th>'+F.month.label+'</th><th>'+F.last_month.label+'</th><th>Difference</th><th>Change</th></tr></thead><tbody>';
 CMP_ROWS.forEach(function(r){
  const av=a[r[1]]||0, bv=b[r[1]]||0, dv=av-bv;
  h+='<tr><td>'+r[0]+'</td><td><b>'+fmtCmp(av,r[2])+'</b></td><td>'+fmtCmp(bv,r[2])+'</td><td>'+(dv>0?'+':'')+fmtCmp(dv,r[2])+'</td><td>'+diffTag(av,bv,r[1]!=='birds_died')+'</td></tr>';
 });
 h+='</tbody></table></div><small>This month: '+F.month.start+' to '+F.month.end+' · Last month: '+F.last_month.start+' to '+F.last_month.end+'</small>';
 document.getElementById('cmp').innerHTML=h;
}
async function loadDash(){
 try{ FARM=await api('/api/dashboard/farm'); }
 catch(e){ say('#m',false,'Could not load the dashboard: '+e.message); return; }
 const t=FARM.today||{};
 document.getElementById('dhead').textContent='Today at a glance — '+niceDate(FARM.date);
 document.getElementById('dsub').innerHTML='👷 '+FARM.workers_sent+' of '+FARM.workers_total+' worker(s) have sent their report today';
 document.getElementById('dMoney').textContent=money(t.amount);
 document.getElementById('dEggs').textContent=fmtNum(t.eggs_collected);
 document.getElementById('dChickens').textContent=fmtNum(t.chickens_sold);
 document.getElementById('dDeaths').textContent=fmtNum(t.birds_died);
 document.getElementById('dReports').textContent=fmtNum(t.reports);
 document.getElementById('dCover').textContent=FARM.workers_sent+' / '+FARM.workers_total;
 const w=document.getElementById('warn');
 w.innerHTML=(FARM.warnings&&FARM.warnings.length)?
  FARM.warnings.map(function(x){ return '<div class="warnbox'+(/mortality|Low stock/i.test(x)?' red':'')+'">'+x+'</div>'; }).join(''):
  '<div class="okbox">✅ Nothing needs your attention right now — everybody reported and stock is fine.</div>';
 barChart('chartMoney',FARM.series,'amount',false);
 barChart('chartEggs',FARM.series,'eggs',false);
 barChart('chartDeaths',FARM.series,'deaths',true);
 renderCmp(FARM);
}
function expCmpCSV(){
 if(!FARM){ alert('Open the dashboard first.'); return; }
 const a=FARM.month.totals||{}, b=FARM.last_month.totals||{};
 const rows=CMP_ROWS.map(function(r){
  const o={what:r[0].replace(/[^\x20-\x7E]/g,'').trim()};
  o[FARM.month.label]=a[r[1]]||0;
  o[FARM.last_month.label]=b[r[1]]||0;
  o.difference=Number(((a[r[1]]||0)-(b[r[1]]||0)).toFixed(2));
  return o;
 });
 toCSV(rows,'month_vs_last_month.csv');
}
async function downloadBackup(){
 try{
  const r=await fetch('/api/backup',{headers:{'Authorization':'Bearer '+tok()}});
  if(!r.ok){ say('#m',false,'Could not build the backup.'); return; }
  const b=await r.blob();
  const a=document.createElement('a');
  a.href=URL.createObjectURL(b);
  a.download='fb_poultry_backup_'+new Date().toISOString().slice(0,10)+'.db';
  a.click();
  document.getElementById('bknote').textContent='✅ Last backup: '+new Date().toLocaleString()+' — keep that file somewhere safe.';
  say('#m',true,'Backup downloaded.');
 }catch(e){ say('#m',false,'Backup failed: '+e.message); }
}

/* ================= PRINT / SAVE AS PDF ================= */
function esc(s){ return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function buildPrint(title, sub, rows, withDate){
 const cols=withDate?13:12;
 let head='<tr><th style="width:26px">#</th><th>Worker</th>'+(withDate?'<th>Date</th>':'')+'<th>Section</th><th>Feed given</th><th>Water</th><th>Eggs collected</th><th>Crates</th><th>Chickens sold</th><th>Died</th><th>Photo</th><th>Amount (GH&#8373;)</th><th>Sales / Notes / Problems</th></tr>';
 let body=rows.map(function(r,i){
  const feed=r.feed_done?((r.feed_bags||0)+' bags / '+(r.feed_kg||0)+' kg'+(r.birds_fed?(' · '+(r.birds_fed)+' birds'):'')):'—';
  const notes=[r.sales_summary, r.problems?('Problem: '+r.problems):'', r.notes?('Note: '+r.notes):'', r.manager_comment?('Manager: '+r.manager_comment):''].filter(Boolean).map(esc).join('<br>');
  return '<tr><td>'+(i+1)+'</td><td><b>'+esc(r.worker_name)+'</b></td>'+(withDate?('<td>'+esc(r.date)+'</td>'):'')+
   '<td>'+esc(r.farm_section||'Main')+'</td><td>'+feed+'</td>'+
   '<td>'+(r.water_done?((r.water_liters||0)+' L'):'—')+'</td>'+
   '<td>'+pnum(r.eggs_collected)+'<br><small>'+pnum(r.eggs_broken)+' broken</small></td>'+
   '<td>'+pnum(r.egg_crates)+' packed<br><small>'+pnum(r.crates_sold)+' sold</small></td>'+
   '<td>'+pnum(r.chickens_sold)+'</td>'+
   '<td>'+pnum(r.birds_died)+(r.death_reason?('<br><small>'+esc(r.death_reason)+'</small>'):'')+'</td>'+
   '<td>'+(r.death_image?'Yes':'—')+'</td>'+
   '<td><b>'+(r.amount||r.sales_total||0).toFixed(2)+'</b></td>'+
   '<td>'+notes+'</td></tr>';
 }).join('');
 if(!rows.length) body='<tr><td colspan="'+cols+'">No report.</td></tr>';
 const A=k=>rows.reduce((x,r)=>x+(r[k]||0),0);
 const AM=rows.reduce((x,r)=>x+((r.amount||0)||(r.sales_total||0)),0);
 const tot='<div class="p-tot"><b>Totals for these '+rows.length+' report(s):</b> Feed '+pnum(A('feed_bags'))+' bags / '+pnum(A('feed_kg'))+' kg &nbsp;·&nbsp; Water '+pnum(A('water_liters'))+' L &nbsp;·&nbsp; Eggs '+pnum(A('eggs_collected'))+' collected ('+pnum(A('egg_crates'))+' crates packed, '+pnum(A('crates_sold'))+' sold, '+pnum(A('eggs_broken'))+' broken) &nbsp;·&nbsp; Chickens sold '+pnum(A('chickens_sold'))+' &nbsp;·&nbsp; Birds died '+pnum(A('birds_died'))+' &nbsp;·&nbsp; <b>Money received: GH&#8373; '+AM.toFixed(2)+'</b></div>';
 return '<div class="p-head"><h1>F &amp; B POULTRY FARM</h1><h2>'+esc(title)+'</h2><h2>'+esc(sub)+'</h2></div>'+
  '<table><thead>'+head+'</thead><tbody>'+body+'</tbody></table>'+tot+
  '<div class="p-foot"><span>Printed on '+new Date().toLocaleString()+' by '+esc(U?U.full_name:'manager')+'</span><span>F &amp; B Poultry Farm Management System</span></div>';
}
function doPrint(html){ document.getElementById('printarea').innerHTML=html; window.print(); }
function printDay(){
 const d=DAYDATE||v('shdate');
 doPrint(buildPrint('DAILY WORKER REPORTS', niceDate(d)+'  ·  '+DAYROWS.length+' report(s) received'+(DAYROWS.length?'':' (none)'), DAYROWS, false));
}
function printArchive(){
 const rows=filteredArchive();
 const sub=(v('arcdate')?('Day: '+v('arcdate')+'  ·  '):'All dates  ·  ')+(v('arcq')?('search: "'+v('arcq')+'"  ·  '):'')+rows.length+' report(s)';
 doPrint(buildPrint('REPORT ARCHIVE', sub, rows, true));
}
function printRecs(){
 const rows=filteredRecs();
 let body=rows.map(function(r,i){
  return '<tr><td>'+(i+1)+'</td><td>'+esc(r.date)+'</td><td>'+esc(r.category)+'</td><td><b>'+esc(r.title)+'</b></td><td>'+esc(r.note||'')+'</td><td>'+((r.amount||0)>0?Number(r.amount).toFixed(2):'—')+'</td></tr>';
 }).join('');
 if(!rows.length) body='<tr><td colspan="6">No record.</td></tr>';
 const tot=rows.reduce((x,r)=>x+(r.amount||0),0);
 doPrint('<div class="p-head"><h1>F &amp; B POULTRY FARM</h1><h2>MY RECORDS (manager&#39;s notebook)</h2><h2>'+rows.length+' record(s)'+(v('recFilter')?(' · type: '+esc(v('recFilter'))):'')+(v('recSearch')?(' · search: "'+esc(v('recSearch'))+'"'):'')+'</h2></div>'+
  '<table><thead><tr><th style="width:26px">#</th><th>Date</th><th>Type</th><th>Title</th><th>Details</th><th>Amount (GH&#8373;)</th></tr></thead><tbody>'+body+'</tbody></table>'+
  '<div class="p-tot"><b>Total amount written on these records: GH&#8373; '+tot.toFixed(2)+'</b></div>'+
  '<div class="p-foot"><span>Printed on '+new Date().toLocaleString()+' by '+esc(U?U.full_name:'manager')+'</span><span>F &amp; B Poultry Farm Management System</span></div>');
}

/* ================= MY RECORDS (manager's notebook) ================= */
function pnum(n){ return Number(n||0).toLocaleString(); }
function todayISO(){ return new Date().toISOString().slice(0,10); }
async function loadRecs(){
 try{ RECS=await api('/api/records'); }
 catch(e){ document.getElementById('recList').innerHTML='<div class="panel">⚠️ Could not load your records: '+e.message+'</div>'; return; }
 renderRecs();
}
function filteredRecs(){
 const q=(v('recSearch')||'').trim().toLowerCase();
 const f=v('recFilter');
 let rows=RECS.slice();
 if(f){ rows=rows.filter(function(r){ return r.category===f; }); }
 if(q){ rows=rows.filter(function(r){ return ((r.title||'')+' '+(r.note||'')+' '+(r.date||'')+' '+(r.category||'')).toLowerCase().indexOf(q)>-1; }); }
 return rows;
}
function renderRecs(){
 const rows=filteredRecs();
 const tot=rows.reduce((x,r)=>x+(r.amount||0),0);
 document.getElementById('recSum').innerHTML='<b>'+rows.length+' record(s)</b>'+(tot?(' · 💰 total of the amounts written here: <b>'+money(tot)+'</b>'):'');
 document.getElementById('recList').innerHTML=rows.length?rows.map(function(r){
  return '<div class="rec"><h4>'+esc(r.title)+'</h4><small>📅 '+esc(r.date||'—')+' · <span class="rectag">'+esc(r.category)+'</span>'+((r.amount||0)>0?('💰 '+money(r.amount)):'')+'</small>'+
   (r.note?('<p>'+esc(r.note)+'</p>'):'')+
   '<div class="row"><button class="btn btn-o" onclick="editRec('+r.id+')">✏️ Edit</button><button class="btn btn-r" onclick="delRec('+r.id+')">🗑 Delete</button></div></div>';
 }).join(''):'<div class="panel">No record yet. Write your first one above — for example a delivery you received — and it will be kept here for you.</div>';
}
function resetRec(){
 ['recTitle','recNote','recAmount'].forEach(function(i){ document.getElementById(i).value=''; });
 document.getElementById('recEdit').value='';
 document.getElementById('recBtn').textContent='💾 Save record';
}
async function addRec(e){
 e.preventDefault();
 const id=v('recEdit');
 const body={date:v('recDate')||todayISO(),category:v('recCat'),title:v('recTitle'),
             note:v('recNote'),amount:v('recAmount')||0};
 try{
  if(id){ await api('/api/records/'+id,{method:'PUT',body:body}); say('#m',true,'Record updated.'); }
  else{ await api('/api/records',{method:'POST',body:body}); say('#m',true,'Record saved — you can see it in the list below.'); }
  resetRec(); loadRecs();
 }catch(err){ say('#m',false,err.message); }
}
function editRec(id){
 const r=RECS.find(x=>x.id===id);
 if(!r) return;
 document.getElementById('recDate').value=r.date||'';
 document.getElementById('recCat').value=r.category||'Note';
 document.getElementById('recTitle').value=r.title||'';
 document.getElementById('recNote').value=r.note||'';
 document.getElementById('recAmount').value=(r.amount||0)>0?r.amount:'';
 document.getElementById('recEdit').value=r.id;
 document.getElementById('recBtn').textContent='💾 Save changes';
 window.scrollTo(0,0);
}
async function delRec(id){
 if(!confirm('Delete this record?')) return;
 try{ await api('/api/records/'+id,{method:'DELETE'}); say('#m',true,'Record deleted.'); loadRecs(); }
 catch(e){ say('#m',false,e.message); }
}
function expRecCSV(){
 const rows=filteredRecs();
 toCSV(rows.map(function(r){ return {date:r.date,category:r.category,title:r.title,note:r.note||'',amount:r.amount||0}; }),'my_records.csv');
}
/* ================= PHOTO (click to see it big) ================= */
function viewImg(src){
 if(!src) return;
 document.getElementById('lbimg').src=src;
 document.getElementById('lb').classList.add('open');
}
function closeImg(){
 document.getElementById('lb').classList.remove('open');
 document.getElementById('lbimg').src='';
}
document.addEventListener('keydown',function(e){ if(e.key==='Escape') closeImg(); });

async function init(){
 document.getElementById('recDate').value=todayISO();
 try{ await api('/api/reminders/check',{method:'POST'}); }catch(e){}
 await Promise.allSettled([loadDash(), loadShift(), loadWorkers(), loadArchive()]);
}
init().catch(()=>say('#m',false,'Something went wrong. Please try again.'));
