const hosted=document.body.dataset.hosted==='true';
const queries=['site:imdb.com/title/ "IronGlass" "technical"','site:imdb.com/title/ "Iron Glass" "technical"','site:imdb.com/title/ "IronGlass" "short"','site:imdb.com/title/ "IronGlass" "music video"','site:imdb.com/title/ "IronGlass" "TV"'];
async function api(path,data){
 if(!hosted)return serverApi(path,data);
 if(path==='/api/results'){
  const res=await fetch('./results.json');if(!res.ok)throw Error('Startgegevens konden niet worden geladen.');
  const seeds=await res.json();let saved=[];
  try{saved=JSON.parse(localStorage.getItem('ironglass.records')||'[]')}catch(e){$('#message').textContent='Browseropslag niet beschikbaar; exporteer wijzigingen voor een back-up.'}
  const merged=new Map(seeds.map(r=>[r.id,r]));for(const row of saved)if(!merged.has(row.id))merged.set(row.id,row);
  return {rows:[...merged.values()],queries};
 }
 if(path==='/api/import'){
  let url;try{url=new URL(data.url)}catch(e){throw Error('Vul een geldige IMDb-link in.')}
  const id=url.pathname.match(/^\/title\/(tt\d+)(?:\/|$)/)?.[1];
  if(!['www.imdb.com','imdb.com','m.imdb.com'].includes(url.hostname)||!['http:','https:'].includes(url.protocol)||!id||!data.title.trim()||!/iron[\s-]*glass/i.test(data.evidence))throw Error('Vul een IMDb-titellink, titel en expliciete IronGlass-vermelding in.');
  if(rows.some(r=>r.id===id))throw Error('Deze productie staat al in het overzicht.');
  const next=[...rows,{id,title:data.title.trim(),year:data.title.match(/\b(?:19|20)\d{2}\b/)?.[0]||'',type:data.type,evidence:data.evidence,url:`https://www.imdb.com/title/${id}/technical/`,status:'Handmatig aangeleverd',checked:new Date().toISOString()}];
  try{localStorage.setItem('ironglass.records',JSON.stringify(next))}catch(e){throw Error('Opslaan in deze browser mislukt. Controleer je browserinstellingen.')}
  return {rows:next};
 }
 throw Error('Deze functie vereist de lokale Python-server.');
}
if(hosted){
 document.querySelector('#scan').textContent='↗ Open onderzoeksopdrachten';
 document.querySelector('#message').textContent='Online versie · toevoegingen blijven in deze browser. Automatisch zoeken is beschikbaar in de lokale versie.';
 document.querySelector('#provider-note').textContent='Gebruik de zoeklinks om IMDb-vermeldingen te ontdekken. Toevoegingen blijven in deze browser en worden niet gedeeld met andere bezoekers. Helios, Mir en Jupiter alleen gelden niet als bewijs voor IronGlass.';
 document.querySelector('#export').onclick=e=>{e.preventDefault();const fields=['id','title','year','type','status','url','evidence','checked'];const cell=v=>'"'+String(/^[=+@-]/.test(String(v))?"'"+v:v??'').replaceAll('"','""')+'"';const csv='\ufeff'+[fields,...rows.map(r=>fields.map(k=>r[k]))].map(row=>row.map(cell).join(',')).join('\r\n');const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='ironglass.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
}
let rows=[];const $=s=>document.querySelector(s);const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function render(){let q=$('#filter').value.toLowerCase(),type=$('#type').value;let filtered=rows.filter(r=>(!type||r.type===type)&&[r.title,r.year,r.evidence].join(' ').toLowerCase().includes(q));$('#total').textContent=rows.length;$('#verified').textContent=rows.filter(r=>r.status==='Gecontroleerd').length;$('#count').textContent=` / ${filtered.length}`;$('#results').innerHTML=filtered.length?filtered.map((r,i)=>`<article><div class="index">${String(i+1).padStart(2,'0')}</div><div class="detail"><div class="meta">${esc(r.type)} · ${esc(r.year||'Jaar onbekend')} <span class="status">${esc(r.status)}</span></div><h3>${esc(r.title)}</h3><p>${esc(r.evidence)}</p><small>Vastgelegd: ${esc(new Date(r.checked).toLocaleDateString('nl-NL'))}</small></div><a class="source" target="_blank" rel="noopener noreferrer" href="${esc(r.url)}">IMDb ↗</a></article>`).join(''):'<div class="empty">Geen vermeldingen voor deze selectie.</div>'}
async function serverApi(path,data){let res=await fetch(path,data?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}:{});let json=await res.json();if(!res.ok)throw Error(json.error||'Verzoek mislukt');return json}
$('#scan').onclick=async()=>{if(hosted){document.querySelector('#queries').scrollIntoView({behavior:'smooth',block:'center'});$('#message').textContent='Kies hieronder een zoekopdracht. Automatisch doorzoeken vereist de lokale Python-server.';return;}let b=$('#scan');b.disabled=true;$('#message').textContent='Zoeken naar expliciete IronGlass-vermeldingen…';try{let data=await api('/api/search',{});rows=data.rows;render();$('#message').textContent=`${data.found} unieke kandidaten gevonden. `+(data.errors.length?'Niet alle zoekopdrachten werkten: '+data.errors.join(' | '):'Zoekronde afgerond. Kandidaten zijn nog niet brongecontroleerd.')}catch(e){$('#message').textContent=e.message}finally{b.disabled=false}};
$('#import').onsubmit=async e=>{e.preventDefault();try{let data=await api('/api/import',Object.fromEntries(new FormData(e.target)));rows=data.rows;render();e.target.reset();$('#message').textContent=hosted?'Opgeslagen in deze browser. Exporteer CSV voor een back-up.':'Bronmateriaal opgeslagen.'}catch(e){$('#message').textContent=e.message}};
$('#filter').oninput=render;$('#type').onchange=render;
api('/api/results').then(data=>{rows=data.rows;render();$('#queries').innerHTML=data.queries.map((q,i)=>`<a target="_blank" rel="noopener noreferrer" href="https://www.google.com/search?q=${encodeURIComponent(q)}">${['IronGlass · algemeen','Iron Glass · schrijfvariant','Shorts','Muziekvideo’s','Televisie'][i]} ↗</a>`).join('')}).catch(e=>$('#message').textContent=e.message);
