const grid=document.getElementById('grid'),count=document.getElementById('count'),
q=document.getElementById('q'),fMarca=document.getElementById('f-marca'),
fPot=document.getElementById('f-pot'),
fOrden=document.getElementById('f-orden'),fFicha=document.getElementById('f-ficha'),
stats=document.getElementById('stats'),dgtBody=document.getElementById('dgt-body'),
q2=document.getElementById('q2'),modalBg=document.getElementById('modal-bg'),modal=document.getElementById('modal');

const marcas=[...new Set(DGT_LIST.map(r=>r[0]))].sort((a,b)=>a.localeCompare(b,'es'));
const FICHAS=new Set(ENRICHED.map(e=>e.marca+'|'+e.modelo));
const fmt=(v,u)=> (v===null||v===undefined||v==='')?'—':(u?v+' '+u:v);
const priceB=e=>{const o=bestOffer(e);return o.p===null?'<b>A consultar</b>':`<b>${e.precioEst?'≈':''}${o.p} €</b>`;};
const bestOffer=e=>{if(e.ofertas&&e.ofertas.length){const v=e.ofertas.filter(o=>o.p!=null).sort((a,b)=>a.p-b.p)[0];if(v)return v;}return {t:e.tienda,u:e.buy,p:e.precio};};
const offerLinks=e=>{if(!(e.ofertas&&e.ofertas.length))return fmt(e.tienda);return `<span class="offers">${e.ofertas.slice().sort((a,b)=>(a.p??1e12)-(b.p??1e12)).map(o=>`<a target="_blank" rel="noopener" href="${o.u}">${o.t}${o.p!=null?` <small>${o.p} €</small>`:''}</a>`).join('')}</span>`;};
const FEAT=new Set();
const ipxLevel=s=>{if(!s)return -1;const m=/IPX?(\d)(\d)?/i.exec(s);if(!m)return -1;return m[2]?+m[2]:+m[1];};
const hasDoubleSusp=s=>!!s&&(/tras/i.test(s)||/dual/i.test(s)||/damping/i.test(s)||/4 brazos/i.test(s)||/offroad/i.test(s));
const R={precio:{lo:0,hi:4000,min:0,max:4000,on:false},aut:{lo:0,hi:150,min:0,max:150,on:false},vel:{lo:0,hi:120,min:0,max:120,on:false}};
function dualSlider(key,fmtVal,step){
  const lo=document.getElementById('r-'+key+'-lo'),hi=document.getElementById('r-'+key+'-hi'),
        fill=document.getElementById('r-'+key+'-fill'),val=document.getElementById('r-'+key+'-val');
  function render(){
    let a=+lo.value,b=+hi.value;
    if(a>b-step){if(document.activeElement===lo){a=b-step;lo.value=a;}else{b=a+step;hi.value=b;}}
    const st=R[key];st.lo=a;st.hi=b;st.on=(a>st.min||b<st.max);
    const p=x=>((x-st.min)/(st.max-st.min)*100);
    fill.style.left=p(a)+'%';fill.style.right=(100-p(b))+'%';
    val.textContent=st.on?fmtVal(a,b):'Todo';
    applyFilters();
  }
  lo.addEventListener('input',render);hi.addEventListener('input',render);
}
dualSlider('precio',(a,b)=>a+' – '+b+' €',50);
dualSlider('aut',(a,b)=>a+' – '+b+' km',5);
dualSlider('vel',(a,b)=>a+' – '+b+' km/h',5);
[['precio',0,4000],['aut',0,150],['vel',0,120]].forEach(([k,a,b])=>{
  const st=R[k],p=x=>((x-st.min)/(st.max-st.min)*100),f=document.getElementById('r-'+k+'-fill');
  f.style.left=p(a)+'%';f.style.right=(100-p(b))+'%';});
let CMP=[];try{CMP=JSON.parse(localStorage.getItem('patdgt_cmp')||'[]');}catch(e){CMP=[];}
const CMPSAVE=()=>{try{localStorage.setItem('patdgt_cmp',JSON.stringify(CMP));}catch(e){}};
const CMPROWS=[
 ['Precio',e=>{const o=bestOffer(e);return o.p===null?'A consultar':(e.precioEst?'≈':'')+o.p+' €';},'min',e=>bestOffer(e).p],
 ['Velocidad legal',e=>'25 km/h',null,null],
 ['Velocidad real',e=>fmt(e.velReal,'km/h'),'max',e=>e.velReal],
 ['Autonomía máx.',e=>fmt(e.autonomia,'km'),'max',e=>e.autonomia],
 ['Potencia nominal',e=>fmt(e.potNom,'W'),'max',e=>e.potNom],
 ['Potencia máxima',e=>fmt(e.potMax,'W'),'max',e=>e.potMax],
 ['Batería',e=>[e.batWh!=null?e.batWh+' Wh':null,e.batAh!=null?e.batAh+' Ah':null,e.volt!=null?e.volt+' V':null].filter(Boolean).join(' · ')||'—','max',e=>e.batWh],
 ['Peso',e=>fmt(e.peso,'kg'),'min',e=>e.peso],
 ['Carga máxima',e=>fmt(e.carga,'kg'),'max',e=>e.carga],
 ['Ruedas',e=>e.rueda==null?'—':e.rueda+'"',null,null],
 ['Frenos',e=>fmt(e.frenos),null,null],
 ['Suspensión',e=>fmt(e.susp),null,null],
 ['Protección',e=>fmt(e.ipx),null,null],
 ['Tiempo de carga',e=>fmt(e.cargaH,'h'),'min',e=>e.cargaH],
 ['Certificado VMP',e=>e.cert,null,null],
 ['Tiendas',e=>offerLinks(e),null,null]
];
function bestIdx(items,dir,numFn){
  if(!dir)return -1;
  let bi=-1,bv=null,n=0;
  items.forEach((e,i)=>{const v=numFn(e);if(v===null||v===undefined)return;n++;
    if(bv===null||(dir==='max'?v>bv:v<bv)){bv=v;bi=i;}});
  return n>1?bi:-1;
}
function openCompare(){
  const items=CMP.map(id=>ENRICHED.find(e=>e.id===id)).filter(Boolean);
  if(!items.length)return;
  const cm=document.getElementById('cmp-modal');
  let h=`<h2 class="cmp-title">Tabla comparativa</h2><div class="cmp-wrap"><table class="cmp-table"><thead><tr><th>Producto</th>${items.map(e=>`<th>${e.marca}<br>${e.modelo}</th>`).join('')}</tr></thead><tbody>`;
  h+=`<tr><td>Foto</td>${items.map(e=>`<td>${e.img?`<img src="${e.img}" alt="" loading="lazy" onerror="this.remove()">`:'🛴'}</td>`).join('')}</tr>`;
  CMPROWS.forEach(([label,fn,dir,numFn])=>{
    const bi=bestIdx(items,dir,numFn);
    h+=`<tr><td>${label}</td>${items.map((e,i)=>`<td${i===bi?' class="best"':''}>${fn(e)}</td>`).join('')}</tr>`;
  });
  h+=`<tr><td>Comprar</td>${items.map(e=>`<td><a class="cmp-buy" target="_blank" rel="noopener" href="${bestOffer(e).u}">🛒 Ver ofertas</a></td>`).join('')}</tr>`;
  h+=`</tbody></table></div><div class="buybox"><button class="btn-sm detail" id="cmp-close">Cerrar</button></div>`;
  cm.innerHTML=h;
  document.getElementById('cmp-bg').classList.add('open');
  document.getElementById('cmp-close').onclick=()=>document.getElementById('cmp-bg').classList.remove('open');
}
function renderCmpBar(){
  const bar=document.getElementById('cmp-bar');
  bar.classList.toggle('open',CMP.length>0);
  document.getElementById('cmp-count').textContent=CMP.length?`${CMP.length}/4 en comparativa`:'';
}
function toggleCmp(id){
  const i=CMP.indexOf(id);
  if(i>=0)CMP.splice(i,1);
  else{if(CMP.length>=4){document.getElementById('cmp-count').textContent='Máximo 4 modelos';return;}CMP.push(id);}
  CMPSAVE();renderCmpBar();
  document.querySelectorAll('[data-cmp="'+id+'"]').forEach(b=>{const on=CMP.includes(id);b.classList.toggle('on',on);b.textContent=on?'✓':'＋';});
}
document.getElementById('cmp-open').onclick=openCompare;
document.getElementById('cmp-clear').onclick=()=>{CMP=[];CMPSAVE();renderCmpBar();applyFilters();};
document.getElementById('cmp-bg').addEventListener('click',e=>{if(e.target.id==='cmp-bg')e.target.classList.remove('open');});
marcas.forEach(m=>{const o=document.createElement('option');o.value=m;o.textContent=m;fMarca.appendChild(o);});

const minP=Math.min(...ENRICHED.map(e=>e.precio)),maxA=Math.max(...ENRICHED.map(e=>e.autonomia));
stats.innerHTML=`<div class="stat"><b>${ENRICHED.length}</b><span>fichas completas</span></div>
<div class="stat"><b>${DGT_LIST.length}</b><span>modelos DGT</span></div>
<div class="stat"><b>${new Set(DGT_LIST.map(r=>r[0])).size}</b><span>marcas DGT</span></div>
<div class="stat"><b>25 km/h</b><span>límite legal VMP</span></div>`;
document.getElementById('total-dgt').textContent=`(${DGT_LIST.length} modelos)`;

function cardHTML(e){
const ph=e.img?`<img loading="lazy" src="${e.img}" alt="${e.marca} ${e.modelo}" onerror="this.remove()">`:'';
return `<div class="card"><div class="photo"><span>🛴</span>${ph}<button class="cmp-toggle${CMP.includes(e.id)?' on':''}" data-cmp="${e.id}" title="Añadir a la comparativa">${CMP.includes(e.id)?'✓':'＋'}</button></div><div class="card-top"><div class="brand">${e.marca}</div>
<h3>${e.modelo}</h3><span class="cert">Cert. VMP ${e.cert}</span></div>
<div class="specs"><div class="spec">${priceB(e)}<span>Precio ${e.precioEst?'estimado':'aprox.'}</span></div>
<div class="spec"><b>${fmt(e.autonomia,'km')}</b><span>Autonomía</span></div>
<div class="spec"><b>${e.potMax!=null?fmt(e.potMax,'W'):fmt(e.potNom,'W')}</b><span>${e.potMax!=null?`Potencia máx${e.potNom?' ('+e.potNom+' nom)':''}`:'Potencia nominal'}</span></div>
<div class="spec"><b>${fmt(e.batWh,'Wh')}</b><span>Batería${e.volt?' '+e.volt+'V':''}</span></div>
<div class="spec"><b>25 km/h</b><span>Vel. legal DGT</span></div>
<div class="spec"><b>${fmt(e.velReal,'km/h')}</b><span>Vel. real hardware</span></div></div>
<div class="price-row"><span class="store">🛒 ${bestOffer(e).t||''}</span></div>
<div class="card-actions"><a class="btn-sm buy" target="_blank" rel="noopener" href="${bestOffer(e).u}">🛒 Comprar</a>
<button class="btn-sm detail" data-id="${e.id}">Ficha</button></div></div>`;
}
function applyFilters(){
let t=q.value.toLowerCase(),list=ENRICHED.filter(e=>{
if(fFicha.checked&&bestOffer(e).p===null)return false;
if(fMarca.value&&e.marca!==fMarca.value)return false;
if(t&&!(e.marca+' '+e.modelo).toLowerCase().includes(t))return false;
if(R.precio.on){const bp=bestOffer(e).p;if(bp===null||bp<R.precio.lo||bp>R.precio.hi)return false;}
if(R.aut.on&&(e.autonomia===null||e.autonomia===undefined||e.autonomia<R.aut.lo||e.autonomia>R.aut.hi))return false;
if(R.vel.on&&(e.velReal===null||e.velReal===undefined||e.velReal<R.vel.lo||e.velReal>R.vel.hi))return false;
if(FEAT.has('nutt')&&!(e.frenos&&/nutt/i.test(e.frenos)))return false;
if(FEAT.has('zoom')&&!(e.frenos&&/zoom/i.test(e.frenos)))return false;
if(FEAT.has('hidr')&&!(e.frenos&&/hidr/i.test(e.frenos)))return false;
if(FEAT.has('r10')&&!(e.rueda!=null&&e.rueda>=10&&e.rueda<11))return false;
if(FEAT.has('r11')&&!(e.rueda!=null&&e.rueda>=11&&e.rueda<12))return false;
if(FEAT.has('ipx5')&&ipxLevel(e.ipx)<5)return false;
if(FEAT.has('ipx6')&&ipxLevel(e.ipx)<6)return false;
if(FEAT.has('doble')&&!hasDoubleSusp(e.susp))return false;
if(fPot.value){const[a,b]=fPot.value.split('-').map(Number);if(e.potMax===null||e.potMax===undefined||e.potMax<a||e.potMax>b)return false;}
return true;});
const num=(v,d)=> (v===null||v===undefined)?d:v;
if(fOrden.value==='precio-asc')list.sort((a,b)=>num(bestOffer(a).p,1e12)-num(bestOffer(b).p,1e12));
if(fOrden.value==='precio-desc')list.sort((a,b)=>num(bestOffer(b).p,-1)-num(bestOffer(a).p,-1));
if(fOrden.value==='autonomia-desc')list.sort((a,b)=>num(b.autonomia,-1)-num(a.autonomia,-1));
if(fOrden.value==='potencia-desc')list.sort((a,b)=>num(b.potMax,-1)-num(a.potMax,-1));
if(fOrden.value==='velreal-desc')list.sort((a,b)=>num(b.velReal,-1)-num(a.velReal,-1));
count.textContent=`Mostrando ${list.length} patinetes con ficha completa (de ${DGT_LIST.length} homologados DGT)`;
grid.innerHTML=list.map(cardHTML).join('')||'<p>Sin resultados. Prueba con otra búsqueda.</p>';
}
[q,fMarca,fPot,fOrden,fFicha].forEach(el=>el.addEventListener('input',applyFilters));
document.getElementById('chips').addEventListener('click',ev=>{
  const b=ev.target.closest('[data-feat]');if(!b)return;
  const f=b.getAttribute('data-feat');
  if(FEAT.has(f)){FEAT.delete(f);b.classList.remove('on');}else{FEAT.add(f);b.classList.add('on');}
  applyFilters();
});

grid.addEventListener('click',ev=>{
const c=ev.target.closest('[data-cmp]');
if(c){toggleCmp(c.getAttribute('data-cmp'));return;}
const b=ev.target.closest('.detail');if(!b)return;
const e=ENRICHED.find(x=>x.id===b.dataset.id);if(!e)return;
const mph=e.img?`<img class="modal-photo" loading="lazy" src="${e.img}" alt="${e.marca} ${e.modelo}" onerror="this.remove()">`:'';
modal.innerHTML=`<h2>${e.marca} · ${e.modelo}</h2>
<p><span class="cert">Certificado VMP: ${e.cert}</span></p>${mph}
<div class="kvs">
<div class="kv"><b>${(()=>{const o=bestOffer(e);return o.p===null?'A consultar':(e.precioEst?'≈':'')+o.p+' €';})()}</b><span>Mejor precio${e.precioEst?' estimado':''}</span></div>
<div class="kv"><b>25 km/h</b><span>Velocidad legal DGT</span></div>
<div class="kv"><b>${fmt(e.velReal,'km/h')}</b><span>Velocidad real hardware</span></div>
<div class="kv"><b>${e.potNom!=null&&e.potMax!=null?e.potNom+' W / '+e.potMax+' W':fmt(e.potMax!=null?e.potMax:e.potNom,'W')}</b><span>Potencia nominal / máx</span></div>
<div class="kv"><b>${[e.batWh!=null?e.batWh+' Wh':null,e.batAh!=null?e.batAh+' Ah':null,e.volt!=null?e.volt+' V':null].filter(Boolean).join(' · ')||'—'}</b><span>Batería</span></div>
<div class="kv"><b>${fmt(e.autonomia,'km')}</b><span>Autonomía máx</span></div>
<div class="kv"><b>${fmt(e.cargaH,'h')}</b><span>Tiempo de carga</span></div>
<div class="kv"><b>${fmt(e.peso,'kg')}${e.carga?' (máx '+e.carga+' kg)':''}</b><span>Peso / carga</span></div>
<div class="kv"><b>${e.rueda===null||e.rueda===undefined?'—':e.rueda+'"'}</b><span>Ruedas</span></div>
<div class="kv"><b>${fmt(e.frenos)}</b><span>Frenos</span></div>
<div class="kv"><b>${fmt(e.susp)}</b><span>Suspensión</span></div>
<div class="kv"><b>${fmt(e.ipx)}</b><span>Protección</span></div>
<div class="kv"><b>${offerLinks(e)}</b><span>Dónde comprar · mejor precio primero</span></div></div>
<p class="small" style="color:#5b6b82">En España los VMP deben circular limitados a 25 km/h; la velocidad real indica la capacidad del hardware (modo sport / deslimitado, solo para uso privado donde la ley lo permita). Todos llevan luces, reflectantes, timbre y nº de bastidor.</p>
<div class="buybox"><a class="btn-sm buy" target="_blank" rel="noopener" href="${bestOffer(e).u}">🛒 Ver ofertas</a>
<button class="btn-sm detail" onclick="document.getElementById('modal-bg').classList.remove('open')">Cerrar</button></div>`;
modalBg.classList.add('open');
});
modalBg.addEventListener('click',e=>{if(e.target===modalBg)modalBg.classList.remove('open');});

function renderDGT(f=''){
const rows=DGT_LIST.filter(r=>(r[0]+' '+r[1]+' '+r[2]).toLowerCase().includes(f.toLowerCase())).slice(0,800);
dgtBody.innerHTML=rows.map(r=>{
const has=ENRICHED.some(e=>e.marca.toLowerCase()===r[0].toLowerCase().split(' ')[0].toLowerCase()||r[1].toLowerCase().includes(e.modelo.split(' ')[0].toLowerCase()));
return `<tr><td><b>${r[0]}</b></td><td>${r[1]}</td><td><code>${r[2]}</code></td><td>${FICHAS.has(r[0]+'|'+r[1])?'<span class="pill">ficha</span>':''}</td></tr>`;}).join('');
}
q2.addEventListener('input',()=>renderDGT(q2.value));
try{const u=new URLSearchParams(location.search);const qq=u.get('q');if(qq){q.value=qq;}}catch(e){}
applyFilters();renderDGT();renderCmpBar();
