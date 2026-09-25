let U = guard('worker'); let PRODS=[]; let SHIMG='';
document.getElementById('who').textContent = U?U.full_name:'';
const today = new Date().toISOString().slice(0,10);
['shd'].forEach(id=>{const e=document.getElementById(id); if(e) e.value=today;});
function show(id){ ['dash','shift','notif'].forEach(x=>document.getElementById(x).style.display=x===id?'block':'none'); const s=document.getElementById('side'); if(s) s.classList.remove('open'); window.scrollTo(0,0); }
/* ---- Appreciation popup shown after a worker sends the report ---- */
const TY_MSG=[
 ['🎉','Thank you for the report!','Great job today. Your report has been sent to the manager safely.'],
 ['🌟','Excellent work!','Thank you for your effort today. The manager has received your report and is grateful.'],
 ['👏','Well done!','Thank you for sending your report on time. The farm is proud of you!'],
 ['🙏','Thank you very much!','Your report has reached the manager. Keep up the good work!'],
 ['💚','A big thank you!','You did well today. Thank you for taking good care of the birds. Your report is safe with the manager.'],
 ['','Great job, champion!','Thank you for your hard work today. Your report has been sent.']];
function showTy(det){
 const p=TY_MSG[Math.floor(Math.random()*TY_MSG.length)];
 document.getElementById('tkemoji').textContent=p[0];
 document.getElementById('tktitle').textContent=p[1];
 document.getElementById('tkmsg').textContent=p[2];
 document.getElementById('tkdet').innerHTML=det||'';
 document.getElementById('tkback').classList.add('open');
}
function hideTy(ev){
 if(ev && ev.target && ev.target.id!=='tkback') return;
 document.getElementById('tkback').classList.remove('open');
}
async function init(){
 try{ await api('/api/reminders/check',{method:'POST'}); }catch(e){}
 const d = await api('/api/dashboard/worker');
 document.getElementById('cards').innerHTML = `<div class="card"><h3>Submitted</h3><div class="big">${d.total_submitted}</div></div><div class="card"><h3>Available</h3><div class="big">${d.available}</div></div><div class="card"><h3>Sold</h3><div class="big">${d.sold_qty}</div></div><div class="card"><h3>Pending</h3><div class="big">${d.pending}</div></div><div class="card"><h3>Approved</h3><div class="big">${d.approved}</div></div><div class="card"><h3>Rejected</h3><div class="big">${d.rejected}</div></div>`;
 document.getElementById('recent').innerHTML = d.recent.length?d.recent.map(p=>`<p>• ${p.name} (${p.quantity}) — ${badge(p.status)}</p>`).join(''):'No activity yet.';
 PRODS = await api('/api/products?status=approved');
 const ns = await api('/api/notifications');
 document.getElementById('nt').innerHTML = ns.length?ns.map(n=>`<div class="panel"><b>${n.title}</b><p>${n.message}</p><button class="btn btn-o" onclick="mark(${n.id})">Mark read</button></div>`).join(''):'No notifications.';
 shCov(await api('/api/shift-reports?date='+today), true);
}
async function mark(id){ await api('/api/notifications/'+id+'/read',{method:'POST'}); init(); }
let SH='daily', SHEDIT=0;
function shLabel(r){ const k=((r&&r.shift)||'daily').toLowerCase();
 const emo={daily:'📋',morning:'🌅',afternoon:'☀️',evening:'🌙'}[k]||'📋';
 return emo+' '+((k==='daily')?'Daily report':k.charAt(0).toUpperCase()+k.slice(1)+' report'); }
function shCov(rows, mine){
 const r0 = rows.length?rows[0]:null;
 const T='\u2705', W='\u23F3';
 document.getElementById('shcov').innerHTML = r0?
  (T+' You have sent your '+shLabel(r0)+' for '+r0.date+' \u2014 '+(r0.seen_by_manager?(T+' checked by the manager'):(W+' not checked by the manager yet'))) :
  (W+' You have NOT sent your report for today yet. Fill every space in the form below, then send it.');
 if(mine){
  document.getElementById('shmylist').innerHTML = rows.length?rows.map(r=>'<div class="panel"><b>'+shLabel(r)+' - '+(r.date||'')+'</b><div class="thankbar">🎉 Thank you for sending this report!<small>The manager has received it safely. Keep up the good work!</small></div>'+(r.seen_by_manager?'✅ checked by manager':'⏳ not checked yet')+'<br><small>Feed: '+(r.feed_done?('✅ '+(r.feed_bags||0)+' bags / '+(r.feed_kg||0)+' kg'):'—')+' · Water: '+(r.water_done?('✅ '+(r.water_liters||0)+' L'):'—')+' · Eggs: '+r.eggs_collected+' ('+(r.egg_crates||0)+' crates) · Sold: '+(r.chickens_sold||0)+' birds / '+(r.crates_sold||0)+' crates · Died: '+r.birds_died+' · 💰 Amount: '+money(r.amount||r.sales_total||0)+'</small>'+(r.death_image?('<div style="margin-top:6px"><img src="'+imgW(r.death_image)+'" alt="mortality photo" style="max-width:180px;border-radius:8px"></div>'):'')+'<p>'+(r.sales_summary?('Stock sales: '+r.sales_summary+' = '+money(r.sales_total)):'No stock sales')+'</p>'+(r.manager_comment?('<p style="background:#ecfdf5;padding:6px;border-radius:6px"><b>💬 Manager\'s comment:</b> '+r.manager_comment+'</p>'):'')+'<div class="row"><button class="btn btn-o" onclick="shLoad('+r.id+')">Edit (except sales)</button><button class="btn btn-r" onclick="shDel('+r.id+')">🗑 Delete</button></div></div>').join(''):'No report for today yet.';
 }
}
function showShImg(){ const p=document.getElementById('shimgprev'); if(p) p.innerHTML = SHIMG?('<img src="'+(SHIMG+(SHIMG.indexOf('?')>-1?'&':'?')+'token='+tok())+'" style="max-width:160px;border-radius:8px">'):'<small style="color:#64748b">No photo attached yet.</small>'; }
function imgW(url){ return url?(url+(url.indexOf('?')>-1?'&':'?')+'token='+tok()):''; }
function shOpts(){ return PRODS.map(p=>'<option value="'+p.id+'">'+p.name+' - '+p.quantity+' left @ '+money(p.price_per_unit)+'</option>').join('')||'<option value="">No stock</option>'; }
function shAddRow(){
 const box=document.getElementById('shrows');
 const div=document.createElement('div');
 div.className='panel';
 div.innerHTML='<div class="grid2"><div><label>Product</label><select class="shp">'+shOpts()+'</select></div><div><label>Qty sold</label><input class="shq" type="number" min="0" value="0"></div></div><div class="row" style="margin-top:8px"><span class="shline" style="font-weight:800"></span><div class="spacer"></div><button type="button" class="btn btn-o" onclick="this.closest(\'.panel\').remove();dCalc2()">Remove</button></div>';
 box.appendChild(div);
 div.querySelector('.shp').onchange=dCalc2;
 div.querySelector('.shq').oninput=dCalc2;
 dCalc2();
}
function dCalc2(){
 let g=0,n=0;
 document.querySelectorAll('#shrows .panel').forEach(function(r){
  const id=r.querySelector('.shp').value;
  const q=parseInt(r.querySelector('.shq').value||0,10);
  const p=PRODS.find(function(x){return x.id==id;});
  const t=(p&&q>0)?q*(p.price_per_unit||0):0;
  r.querySelector('.shline').textContent=(p&&q>0)?(p.name+' x '+q+' = '+money(t)):'';
  g+=t; if(q>0)n++;
 });
 const el=document.getElementById('shgrand');
 if(el) el.textContent=n?('Total: '+money(g)+' ('+n+' line'+(n>1?'s':'')+')'):'';
}
async function shLoad(id){
 try{
  const all=await api('/api/shift-reports');
  const r=all.find(x=>x.id===id); if(!r) return;
  if(r.sale_ids || (r.sales_summary && r.sales_summary.length)){
   say('#m',false,'That report already has sales lines. Submitted reports are permanent and cannot be changed.');
  }
  SHEDIT=id; SHIMG=r.death_image||''; showShImg();
  document.getElementById('shd').value=r.date||today;
  document.getElementById('shs').value=r.farm_section||'Main';
  document.getElementById('shfeed').checked=!!r.feed_done;
  document.getElementById('shfq').value=r.feed_qty||'';
  document.getElementById('shfb').value=r.feed_bags||0;
  document.getElementById('shfk').value=r.feed_kg||0;
  document.getElementById('shbf').value=r.birds_fed||0;
  document.getElementById('shwat').checked=!!r.water_done;
  document.getElementById('shwl').value=r.water_liters||0;
  document.getElementById('shwn').value=r.water_notes||'';
  document.getElementById('shec').value=r.eggs_collected||0;
  document.getElementById('shec2').value=r.egg_crates||0;
  document.getElementById('sheb').value=r.eggs_broken||0;
  document.getElementById('shcs').value=r.chickens_sold||0;
  document.getElementById('shks').value=r.crates_sold||0;
  document.getElementById('shdd').value=r.birds_died||0;
  document.getElementById('shdr').value=r.death_reason||'';
  document.getElementById('sham').value=r.amount||0;
  document.getElementById('shpr').value=r.problems||'';
  document.getElementById('shnt').value=r.notes||'';
  document.getElementById('shrows').innerHTML='';
  say('#m',true,'Editing your '+shLabel(r)+' (sales lines cannot be changed here).');
 }catch(e){ say('#m',false,e.message); }
}
async function shDel(id){
 if(!confirm('Delete this report? This cannot be undone.')) return;
 try{ const j=await api('/api/shift-reports/'+id,{method:'DELETE'}); say('#m',true,j.message||'Report deleted.'); SHEDIT=0; init(); }
 catch(err){ say('#m',false,err.message); }
}
async function uploadImage(){
 const f=document.getElementById('shimg').files[0];
 if(!f) return '';
 const fd=new FormData(); fd.append('file',f);
 const r=await fetch('/api/uploads',{method:'POST',headers:{'Authorization':'Bearer '+tok()},body:fd});
 let j={}; try{ j=await r.json(); }catch(e){}
 if(!r.ok) throw new Error(j.error||'Image upload failed.');
 return j.url||'';
}
async function shSubmit(e){
 e.preventDefault();
 const body={date:val('shd'),shift:'daily',farm_section:val('shs'),
  feed_done:document.getElementById('shfeed').checked,feed_qty:val('shfq'),
  feed_bags:parseFloat(val('shfb')||0),feed_kg:parseFloat(val('shfk')||0),
  birds_fed:parseInt(val('shbf')||0,10),
  water_done:document.getElementById('shwat').checked,
  water_liters:parseFloat(val('shwl')||0),water_notes:val('shwn'),
  eggs_collected:parseInt(val('shec')||0,10),egg_crates:parseInt(val('shec2')||0,10),
  eggs_broken:parseInt(val('sheb')||0,10),
  chickens_sold:parseInt(val('shcs')||0,10),crates_sold:parseInt(val('shks')||0,10),
  birds_died:parseInt(val('shdd')||0,10),death_reason:val('shdr'),
  payment_method:val('shpm'),problems:val('shpr'),notes:val('shnt'),
  amount:parseFloat(val('sham')||0)};
 try{ const url=await uploadImage(); if(url) body.death_image=url; }
 catch(err){ say('#m',false,err.message); return; }
 if(!body.death_image && SHEDIT && SHIMG) body.death_image=SHIMG;
 // an edit is sent only after the empty-space check below, so an
 // incomplete report cannot be saved either
 const lines=[];
 document.querySelectorAll('#shrows .panel').forEach(function(r){
  const q=parseInt(r.querySelector('.shq').value||0,10);
  if(q>0) lines.push({product_id:r.querySelector('.shp').value,quantity:q});
 });
 body.sales=lines;
 const miss=[];
 [['shd','Date'],['shs','Farm section'],['shks','Egg crates sold'],['shcs','Live chickens sold'],
  ['shdd','Birds died'],['shdr','Reason for the deaths'],['shfq','Feed type / note'],
  ['shfb','Feed used (bags)'],['shfk','Feed used (kg)'],['shbf','Birds fed (count)'],
  ['shwl','Water used (litres)'],['shwn','Water notes'],['shec','Eggs collected'],
  ['shec2','Egg crates packed'],['sheb','Eggs broken / spoilt'],
  ['sham','Total amount you got (GH\u20b5)'],['shpr','Other activities / problems'],
  ['shnt','Notes for manager']].forEach(function(p){
   if(!String(val(p[0])||'').trim()) miss.push(p[1]);
  });
 if(body.birds_died>0 && !body.death_image) miss.push('📷 Photo of the dead bird(s)');
 if(miss.length){
  say('#m',false,'You cannot send the report yet. Still empty: '+miss.join(', ')+
      '. Write 0 for a number or None for words if nothing happened.'); return;
 }
 if(SHEDIT){
  // sales lines are permanent records and are never re-sent when editing
  delete body.sales;
  try{ const j=await api('/api/shift-reports/'+SHEDIT,{method:'PUT',body:body}); say('#m',true,j.message); SHEDIT=0; init(); }
  catch(err){ say('#m',false,err.message); }
  return;
 }
 try{
  const j=await api('/api/shift-reports',{method:'POST',body:body});
  say('#m',true,j.message);
  const det=['<b>📅 Date:</b> '+(body.date||''),
   '<b>🍽️ Feed:</b> '+(body.feed_bags||0)+' bags / '+(body.feed_kg||0)+' kg',
   '<b>💧 Water:</b> '+(body.water_liters||0)+' litres',
   '<b>🥚 Eggs collected:</b> '+(body.eggs_collected||0)+' ('+(body.egg_crates||0)+' crates packed)',
   '<b>🐔 Chickens sold:</b> '+(body.chickens_sold||0),
   '<b>💰 Amount you got:</b> '+money(body.amount||0)].join('<br>');
  showTy(det);
  document.getElementById('shrows').innerHTML='';
  document.getElementById('shpr').value='';document.getElementById('shnt').value='';
  document.getElementById('shfq').value='';document.getElementById('shwn').value='';
  document.getElementById('shimg').value=''; SHIMG=''; showShImg();
  ['shbf','shdd','shec','shec2','sheb','shfb','shfk','shwl','shcs','shks','sham'].forEach(function(x){document.getElementById(x).value=0;});
  init();
 }catch(err){ say('#m',false,err.message); }
}
document.getElementById('shimg').addEventListener('change',function(){
 const f=this.files[0];
 if(f){ const rd=new FileReader(); rd.onload=ev=>{ SHIMG=ev.target.result; showShImg(); }; rd.readAsDataURL(f); }
});
function val(id){ return document.getElementById(id).value; }
showShImg();
init().catch(e=>say('#m',false,'Could not load the dashboard: '+((e&&e.message)||e)));