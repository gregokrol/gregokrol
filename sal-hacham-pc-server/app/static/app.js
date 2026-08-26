const $=s=>document.querySelector(s);
const state={lat:null,lng:null,storesDirty:true,storesLoaded:false,searchController:null,storesController:null,healthLoaded:false,basketSeq:0,storeOffers:new Map()};
function esc(s){return String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
function fmtDate(s){if(!s)return '';const d=new Date(s);return Number.isNaN(d.getTime())?'':d.toLocaleString('he-IL')}
function money(v){return `₪${Number(v||0).toFixed(2)}`}
function selectedChains(){return [...document.querySelectorAll('#chains input:checked')].map(x=>x.value)}
function locationParams(){
  const p=new URLSearchParams({radius_km:$('#radius').value});
  if($('#city').value)p.set('city',$('#city').value);
  if(state.lat!=null){p.set('lat',state.lat);p.set('lng',state.lng)}
  selectedChains().forEach(x=>p.append('chain',x));
  return p;
}
function locationBody(){return {city:$('#city').value||null,lat:state.lat,lng:state.lng,radius_km:Number($('#radius').value),chains:selectedChains().length?selectedChains():null}}
function updateChainsSummary(){const selected=selectedChains();$('#chainsSummary').textContent=selected.length?`${selected.length} נבחרו`:'הכול'}
function storesOpen(){return !$('#storesBody').hidden}
function setStoresOpen(open){const body=$('#storesBody');const toggle=$('#storesToggle');body.hidden=!open;toggle.setAttribute('aria-expanded',String(open));$('#storesPanel').classList.toggle('is-open',open);if(open)loadStores();else if(state.storesController){state.storesController.abort();state.storesController=null}}
function markStoresDirty(){state.storesDirty=true;if(!storesOpen())$('#storesSummary').textContent=state.storesLoaded?'נדרש רענון':'לחץ להצגה'}

function offerBadge(o){
  const cls=o.is_coupon?'coupon':'promo';
  const icon=o.is_coupon?'🎟️':'🏷️';
  return `<span class="offer-badge ${cls}">${icon} ${esc(o.description)}</span>`;
}

async function init(){
  setStoresOpen(false);
  const [h,cities,chains]=await Promise.all([
    fetch('/api/health').then(r=>r.json()),
    fetch('/api/cities').then(r=>r.json()),
    fetch('/api/chains').then(r=>r.json())
  ]);
  const status=$('#status');
  if(h.live_ready && h.real_stores){status.textContent=`${h.fresh_real_stores}/${h.real_stores} סניפים עם מידע טרי`;status.classList.add(h.coverage_complete?'live':'partial')}
  else if(h.real_prices){status.textContent=`יש נתונים אמיתיים, אך לא מה־${h.max_age_hours} שעות האחרונות`;status.classList.add('demo')}
  else if(h.total_prices){status.textContent='מצב בדיקה — אין עדיין נתונים חיים';status.classList.add('demo')}
  else{status.textContent='אין נתוני מחיר';status.classList.add('demo')}
  if(h.active_promotions)status.title=`${h.active_promotions} מבצעים פעילים, ${h.active_coupons||0} קופונים`;
  if(h.cached_city_count!=null)status.title=`${status.title?status.title+' · ':''}${h.cached_city_count}/${h.max_cached_cities} ערים שמורות${h.active_city?' · פעילה: '+h.active_city:''}`;
  const hint=$('#freshnessHint');if(hint)hint.textContent=`מוצגים רק מחירים שאומתו מול מקור ב־${h.max_age_hours} השעות האחרונות. מבצעים וקופונים נבדקים גם לפי תוקף הפרסום.`;
  for(const city of cities.cities){const o=document.createElement('option');o.value=o.textContent=city;$('#city').append(o)}
  $('#chains').innerHTML=chains.chains.map(x=>`<label class="chip"><input type="checkbox" value="${esc(x.key)}">${esc(x.name)}${x.stores?` (${x.stores})`:''}</label>`).join('');
  $('#chains').addEventListener('change',()=>{updateChainsSummary();markStoresDirty();if(storesOpen())loadStores()});
  updateChainsSummary();
  addBasketRow('חלב 3%',1);addBasketRow('שוקו',1);
}

async function loadStores(force=false){
  if(!force && !state.storesDirty && state.storesLoaded)return;
  if(!storesOpen() && !force)return;
  const city=$('#city').value;
  if(!city && state.lat==null){
    $('#storesList').innerHTML='<p class="hint">בחר עיר או הפעל GPS כדי להציג את החנויות הרלוונטיות.</p>';
    $('#storesSummary').textContent='בחר מיקום';state.storesLoaded=false;return;
  }
  if(state.storesController)state.storesController.abort();
  const controller=new AbortController();state.storesController=controller;
  $('#storesList').innerHTML='<p class="hint">טוען חנויות…</p>';$('#storesSummary').textContent='טוען…';
  try{
    const data=await fetch('/api/stores?'+locationParams(),{signal:controller.signal}).then(async r=>{if(!r.ok)throw new Error((await r.json()).detail||r.statusText);return r.json()});
    if(state.storesController!==controller)return;
    state.storesLoaded=true;state.storesDirty=false;
    $('#storesSummary').textContent=data.count?`${data.count} חנויות`:'אין חנויות';
    if(!data.stores.length){$('#storesList').innerHTML='<p class="hint">לא נמצאו חנויות באזור שנבחר.</p>';return}
    $('#storesList').innerHTML=data.stores.map(s=>{
      const offerText=s.active_coupons?`🎟️ ${s.active_coupons} קופונים · 🏷️ ${s.active_promotions||0} מבצעים`:s.active_promotions?`🏷️ ${s.active_promotions} מבצעים`:'אין מבצע/קופון טרי שפורסם';
      return `<div class="store-card" data-store-id="${esc(s.id)}">
        <button class="store-row store-main" type="button" aria-expanded="false">
          <div><strong>${esc(s.chain_name)}</strong><div>${esc(s.name)}</div>
            <div class="meta">${esc(s.city||'')}${s.address?' · '+esc(s.address):''}</div>
            <div class="freshness ${s.fresh_prices?'fresh':'stale'}">${s.fresh_prices?`${s.fresh_prices} מחירים טריים`:'אין כרגע מחיר טרי'} · ${esc(offerText)}</div>
            <div class="store-click-hint">לחץ להצגת מבצעים וקופונים</div>
          </div>${s.distance_km!=null?`<span class="distance">${s.distance_km} ק״מ</span>`:''}
        </button><div class="store-offers" hidden></div></div>`;
    }).join('');
  }catch(e){if(e.name!=='AbortError'){ $('#storesSummary').textContent='שגיאה';$('#storesList').innerHTML=`<p class="error">לא ניתן לטעון חנויות: ${esc(e.message)}</p>`}}
  finally{if(state.storesController===controller)state.storesController=null}
}

async function toggleStoreOffers(card){
  const btn=card.querySelector('.store-main');const body=card.querySelector('.store-offers');const storeId=card.dataset.storeId;
  const open=body.hidden;
  if(!open){body.hidden=true;btn.setAttribute('aria-expanded','false');return}
  body.hidden=false;btn.setAttribute('aria-expanded','true');
  if(body.dataset.loaded==='1')return;
  body.innerHTML='<p class="hint">טוען מבצעים וקופונים…</p>';
  try{
    const data=await fetch('/api/store-offers?'+new URLSearchParams({store_id:storeId})).then(async r=>{if(!r.ok)throw new Error((await r.json()).detail||r.statusText);return r.json()});
    let html=`<div class="offers-head"><strong>${data.coupon_count} קופונים · ${data.promotion_count||0} מבצעים פעילים</strong><span class="hint-inline">מקור טרי עד ${data.max_age_hours} שעות</span></div>`;
    if(data.official_benefits){html+=`<a class="official-link" href="${esc(data.official_benefits.url)}" target="_blank" rel="noopener noreferrer">↗ ${esc(data.official_benefits.label)}</a><div class="hint">${esc(data.official_benefits.note)}</div>`}
    if(!data.offers.length)html+='<p class="hint">לא נמצא כרגע מבצע/קופון פעיל וטרי בקובצי השקיפות של הסניף.</p>';
    else html+=`<div class="offer-list">${data.offers.map(o=>`<article class="offer-card ${o.is_coupon?'coupon-card':''}">
      <div class="offer-title">${o.is_coupon?'🎟️ קופון':'🏷️ מבצע'} — ${esc(o.description)}</div>
      <div class="meta">${o.discounted_price!=null?`מחיר מבצע: ${money(o.discounted_price)}${o.min_qty?` ל־${Number(o.min_qty)} יח׳`:''} · `:''}${o.saving>0?`חיסכון: ${money(o.saving)} · `:''}${o.end_at?`בתוקף עד ${fmtDate(o.end_at)}`:'ללא מועד סיום שפורסם'}${o.club_ids?.length?' · מועדון: '+esc(o.club_ids.join(', ')):''}</div>
      ${o.items?.length?`<div class="offer-items">${o.items.map(i=>`<span>${i.is_gift?'🎁 ':''}${esc(i.name||i.barcode)}</span>`).join('')}</div>`:''}
    </article>`).join('')}</div>`;
    if(data.truncated)html+='<p class="hint">מוצגים המבצעים הראשונים בלבד.</p>';
    html+='<p class="coupon-note">קופון עשוי להיות אישי או מותנה בחברות מועדון/אמצעי תשלום. המערכת מציגה את מה שהרשת פרסמה אך אינה קובעת זכאות אישית.</p>';
    body.innerHTML=html;body.dataset.loaded='1';
  }catch(e){body.innerHTML=`<p class="error">לא ניתן לטעון מבצעים: ${esc(e.message)}</p>`}
}

async function search(){
  const q=$('#q').value.trim();if(!q){$('#message').textContent='כתוב מוצר לחיפוש.';return}
  if(state.searchController)state.searchController.abort();
  const controller=new AbortController();state.searchController=controller;
  const p=locationParams();p.set('q',q);
  const button=$('#search');const oldText=button.textContent;button.disabled=true;button.textContent='מחפש…';
  $('#message').textContent='מחפש…';$('#results').innerHTML='';
  try{
    const data=await fetch('/api/search?'+p,{signal:controller.signal}).then(async r=>{if(!r.ok)throw new Error((await r.json()).detail||r.statusText);return r.json()});
    const cache=data.city_cache;const cacheText=cache?.refresh_in_progress?(cache.last_refresh_at?'העיר מתרעננת ברקע; מוצג המטמון האחרון. ':'הסריקה הראשונה של העיר התחילה; התוצאות יופיעו לאחר השלמתה. '):cache?.last_refresh_at?`מטמון העיר עודכן לאחרונה ב־${fmtDate(cache.last_refresh_at)}. `:'';
    if(!data.results.length){$('#message').textContent=cacheText+'לא נמצאה התאמה מדויקת עם מחיר טרי. נסה שוב לאחר הרענון או דייק את החיפוש.';return}
    $('#message').textContent=cacheText+(data.truncated?`מציג ${data.count} תוצאות ראשונות. צמצם עיר/טווח או דייק את החיפוש.`:`נמצאו ${data.count} מחירים תואמים.`);
    $('#results').innerHTML=data.results.map(r=>`<article class="card"><div><div class="product">${esc(r.product_name)} ${r.is_demo?'<span class="demo-tag">נתון בדיקה</span>':''}</div><div>${esc(r.chain_name)} — ${esc(r.store_name)}</div>
      ${r.offers?.length?`<div class="offer-badges">${r.offers.map(offerBadge).join('')}</div>`:''}
      ${r.history?`<div class="price-history"><span>נמוך ${money(r.history.low_price)}</span><span>ממוצע ${money(r.history.average_price)}</span><span>גבוה ${money(r.history.high_price)}</span><small>עד ${r.history.period_days} יום · ${r.history.days_observed} ימי מדידה · ${r.history.sample_count} דגימות</small></div>`:''}
      <div class="meta">${esc(r.city||'')} ${r.address?'· '+esc(r.address):''}${r.distance_km!=null?' · '+r.distance_km+' ק״מ':''}<br>אומת מול קובץ: ${fmtDate(r.observed_at)} · שינוי מחיר: ${fmtDate(r.updated_at)}</div></div><div class="price">${money(r.price)}</div></article>`).join('');
  }catch(e){if(e.name!=='AbortError')$('#message').innerHTML=`<span class="error">שגיאה: ${esc(e.message)}</span>`}
  finally{if(state.searchController===controller){state.searchController=null;button.disabled=false;button.textContent=oldText}}
}

function addBasketRow(value='',qty=1){
  const id=++state.basketSeq;const row=document.createElement('div');row.className='basket-row';row.dataset.id=id;
  row.innerHTML=`<input class="basket-q" placeholder="מוצר, למשל קפה נמס" value="${esc(value)}" autocomplete="off"><input class="basket-qty" type="number" min="0.1" max="100" step="0.1" value="${Number(qty)}" aria-label="כמות"><button class="remove-row ghost" type="button" aria-label="מחק מוצר">✕</button>`;
  row.querySelector('.remove-row').addEventListener('click',()=>{if($('#basketRows').children.length>1)row.remove();else{row.querySelector('.basket-q').value='';row.querySelector('.basket-qty').value='1'}});
  $('#basketRows').append(row);
}
function basketItems(){return [...document.querySelectorAll('.basket-row')].map(r=>({q:r.querySelector('.basket-q').value.trim(),qty:Number(r.querySelector('.basket-qty').value)})).filter(x=>x.q&&x.qty>0)}

async function compareBasket(){
  const items=basketItems();if(!items.length){$('#basketMessage').textContent='הוסף לפחות מוצר אחד לסל.';return}
  const btn=$('#compareBasket');const old=btn.textContent;btn.disabled=true;btn.textContent='משווה…';$('#basketMessage').textContent='משווה את הסל…';$('#basketResults').innerHTML='';
  try{
    const payload={...locationBody(),items,include_coupons:$('#includeCoupons').checked};
    const data=await fetch('/api/basket',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}).then(async r=>{if(!r.ok){const e=await r.json();throw new Error(e.detail?JSON.stringify(e.detail):r.statusText)}return r.json()});
    if(!data.stores.length){$('#basketMessage').textContent='לא נמצאו סניפים עם נתונים טריים באזור שנבחר.';return}
    const complete=data.stores.filter(s=>s.missing_count===0).length;
    $('#basketMessage').textContent=complete?`${complete} סניפים מכילים את כל פריטי הסל. המחיר הזול ביותר מוצג ראשון.`:'לא נמצא סניף שמכיל את כל הפריטים; הסניפים מדורגים לפי מספר הפריטים שנמצאו ואז לפי מחיר.';
    $('#basketResults').innerHTML=data.stores.map(s=>`<article class="basket-card ${s.missing_count?'incomplete':''}">
      <div class="basket-rank">#${s.rank}</div><div class="basket-store"><strong>${esc(s.chain_name)} — ${esc(s.store_name)}</strong><div class="meta">${esc(s.city||'')}${s.address?' · '+esc(s.address):''}${s.distance_km!=null?' · '+s.distance_km+' ק״מ':''}</div>
      <div class="basket-tags"><span>${s.coverage_pct}% מהסל</span>${s.offer_matches?`<span>🏷️ מבצעים ל־${s.offer_matches} פריטים</span>`:''}${s.coupon_matches?`<span>🎟️ קופונים ל־${s.coupon_matches} פריטים</span>`:''}</div></div>
      <div class="basket-total"><strong>${money(s.total)}</strong>${s.savings>0?`<span class="saving">חיסכון ${money(s.savings)}</span><del>${money(s.base_total)}</del>`:''}${s.missing_count?`<span class="missing">חסרים ${s.missing_count}</span>`:''}</div>
      <details class="basket-lines"><summary>פירוט הסל</summary><div>${s.lines.map(l=>l.missing?`<div class="basket-line missing-line"><span>${esc(l.query)}</span><span>לא נמצא</span></div>`:`<div class="basket-line"><span>${esc(l.product_name)} × ${Number(l.qty)}</span><span>${money(l.total_after_offer??l.line_total)}</span>${l.applied_offer?`<small>${l.applied_offer.is_coupon?'🎟️':'🏷️'} ${esc(l.applied_offer.description)}</small>`:l.offers_available?'<small>יש מבצע שאינו מחושב אוטומטית</small>':''}</div>`).join('')}</div></details>
    </article>`).join('');
    const note=document.createElement('p');note.className='hint';note.textContent=data.calculation_note;$('#basketResults').append(note);
  }catch(e){$('#basketMessage').innerHTML=`<span class="error">שגיאה בהשוואת הסל: ${esc(e.message)}</span>`}
  finally{btn.disabled=false;btn.textContent=old}
}

async function loadDataHealth(){
  if(state.healthLoaded)return;$('#healthSummary').textContent='טוען…';$('#healthBody').innerHTML='<p class="hint">בודק כיסוי נתונים…</p>';
  try{
    const data=await fetch('/api/data-health').then(async r=>{if(!r.ok)throw new Error(r.statusText);return r.json()});state.healthLoaded=true;
    $('#healthSummary').textContent=data.chains.length?`${data.chains.length} רשתות`:'אין נתוני Live';
    if(!data.chains.length){$('#healthBody').innerHTML=`<p class="hint">אין עדיין נתוני רשת אמיתיים. מנוע החיפוש המהיר: ${data.fts_enabled?'פעיל':'מצב תאימות'}.</p>`;return}
    $('#healthBody').innerHTML=`<div class="health-list">${data.chains.map(c=>`<div class="health-row"><div><strong>${esc(c.chain_name)}</strong><div class="meta">עדכון מחיר אחרון: ${c.latest_price_at?fmtDate(c.latest_price_at):'אין'}</div></div><div class="health-metrics"><span class="coverage ${c.coverage_pct===100?'good':c.coverage_pct?'partial':'bad'}">${c.fresh_stores}/${c.total_stores} סניפים · ${c.coverage_pct}%</span><span>🏷️ ${c.active_promotions}</span><span>🎟️ ${c.active_coupons}</span></div></div>`).join('')}</div><p class="hint">מנוע חיפוש FTS: ${data.fts_enabled?'פעיל':'לא זמין — פועל fallback מלא'}.</p>`;
  }catch(e){$('#healthSummary').textContent='שגיאה';$('#healthBody').innerHTML=`<p class="error">לא ניתן לטעון בריאות נתונים: ${esc(e.message)}</p>`}
}

$('#search').addEventListener('click',search);$('#q').addEventListener('keydown',e=>{if(e.key==='Enter')search()});
$('#gps').addEventListener('click',()=>{if(!navigator.geolocation){$('#message').textContent='הדפדפן לא תומך במיקום.';return}navigator.geolocation.getCurrentPosition(pos=>{state.lat=pos.coords.latitude;state.lng=pos.coords.longitude;$('#city').value='';$('#gps').textContent='📍 מיקום פעיל';$('#clearGps').hidden=false;$('#message').textContent='המיקום התקבל. החיפוש והסל הבאים יהיו לפי מרחק.';markStoresDirty();if(storesOpen())loadStores()},err=>{$('#message').textContent='לא ניתן לקבל מיקום: '+err.message},{enableHighAccuracy:true,timeout:10000})});
$('#clearGps').addEventListener('click',()=>{state.lat=state.lng=null;$('#gps').textContent='📍 השתמש במיקום שלי';$('#clearGps').hidden=true;markStoresDirty();if(storesOpen())loadStores()});
$('#city').addEventListener('change',()=>{if($('#city').value&&state.lat!=null){state.lat=state.lng=null;$('#gps').textContent='📍 השתמש במיקום שלי';$('#clearGps').hidden=true;$('#message').textContent='מצב עיר ידנית פעיל.'}markStoresDirty();if(storesOpen())loadStores()});
$('#radius').addEventListener('change',()=>{markStoresDirty();if(storesOpen())loadStores()});
$('#storesToggle').addEventListener('click',()=>setStoresOpen(!storesOpen()));
$('#refreshStores').addEventListener('click',()=>{state.storesDirty=true;state.storeOffers.clear();loadStores(true)});
$('#storesList').addEventListener('click',e=>{const btn=e.target.closest('.store-main');if(btn)toggleStoreOffers(btn.closest('.store-card'))});
$('#addBasketRow').addEventListener('click',()=>addBasketRow('',1));$('#compareBasket').addEventListener('click',compareBasket);
$('#dataHealthPanel').addEventListener('toggle',()=>{if($('#dataHealthPanel').open)loadDataHealth()});
init().catch(e=>{$('#message').textContent='שגיאת אתחול: '+e.message});
