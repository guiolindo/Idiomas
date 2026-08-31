// =========================================================================
// STATE + PERSISTENCE
// =========================================================================
const API_BASE = window.API_BASE || '';
const LS_KEY = 'idiomas.v1';
const state = {
  lang: 'en',
  cue: 'pt',        // pt | emoji | foto | mix
  notebook: false,
  order: 'rand',    // rand | seq
  theme: 'auto',
  known: {},        // { topicId: { wordIdx: true } }
  streak: { lastDate: null, count: 0 },
  lastStudied: null, // { topicId, i } — para o banner "continuar"
  currentCat: null,
  queue: [],
  i: 0,
  revealed: false,
  sessionMissed: [], // [{idx}] — não persistido, só durante a rodada atual
};
let TOPICS = [];
let filterState = { text: '', chip: 'all' };

function loadState(){
  try{
    const s = JSON.parse(localStorage.getItem(LS_KEY)||'{}');
    Object.assign(state, s);
    if(!state.streak) state.streak = { lastDate: null, count: 0 };
  }catch(_){}
}
function saveState(){
  const {lang,cue,notebook,order,theme,known,streak,lastStudied} = state;
  localStorage.setItem(LS_KEY, JSON.stringify({lang,cue,notebook,order,theme,known,streak,lastStudied}));
}

// =========================================================================
// HELPERS
// =========================================================================
const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);
const rand = (n) => Math.floor(Math.random()*n);
function shuffled(arr){
  const a = arr.slice();
  for(let i=a.length-1;i>0;i--){
    const j=rand(i+1); [a[i],a[j]]=[a[j],a[i]];
  }
  return a;
}
function fold(s){
  return (s||'').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'').replace(/[^a-z0-9 ']/g,'').trim();
}
function levenshtein(a,b){
  if(a===b) return 0;
  if(!a.length) return b.length;
  if(!b.length) return a.length;
  const v0 = new Array(b.length+1);
  const v1 = new Array(b.length+1);
  for(let i=0;i<=b.length;i++) v0[i]=i;
  for(let i=0;i<a.length;i++){
    v1[0] = i+1;
    for(let j=0;j<b.length;j++){
      const cost = a[i]===b[j]?0:1;
      v1[j+1] = Math.min(v1[j]+1, v0[j+1]+1, v0[j]+cost);
    }
    for(let j=0;j<=b.length;j++) v0[j]=v1[j];
  }
  return v1[b.length];
}
function matchAnswer(input, target){
  const a = fold(input), b = fold(target);
  if(!a) return 'empty';
  if(a === b) return 'ok';
  const b2 = b.replace(/^to /,'');
  const a2 = a.replace(/^to /,'');
  if(a2 === b2) return 'ok';
  const d = Math.min(levenshtein(a,b), levenshtein(a2,b2));
  const len = Math.max(b.length, 4);
  if(d <= 1 || d/len < 0.18) return 'close';
  return 'no';
}
function countKnown(topicId){
  return Object.keys(state.known[topicId]||{}).length;
}
function todayStr(){ return new Date().toISOString().slice(0,10); }

// =========================================================================
// DATA
// =========================================================================
async function loadTopics(){
  const res = await fetch(`${API_BASE}/api/topics`);
  if(!res.ok) throw new Error('Falha ao carregar tópicos');
  const data = await res.json();
  TOPICS = data.topics;
}

// =========================================================================
// STREAK
// =========================================================================
function bumpStreak(){
  const today = todayStr();
  if(state.streak.lastDate === today) return;
  const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0,10);
  state.streak.count = (state.streak.lastDate === yesterday) ? state.streak.count + 1 : 1;
  state.streak.lastDate = today;
  saveState();
}
function streakText(){
  const today = todayStr();
  const n = state.streak.count || 0;
  if(n === 0) return 'Comece hoje a sua sequência 🔥';
  if(state.streak.lastDate === today) return `${n} ${n===1?'dia seguido':'dias seguidos'} 🔥 — hoje contou`;
  return `${n} ${n===1?'dia seguido':'dias seguidos'} 🔥 — estude hoje pra manter`;
}

// =========================================================================
// HOME
// =========================================================================
function updateStatsCard(){
  let totalKnown = 0, totalWords = 0;
  TOPICS.forEach(t => { totalKnown += countKnown(t.id); totalWords += t.words.length; });
  const pct = totalWords ? totalKnown/totalWords : 0;
  const r = 27, circ = 2*Math.PI*r;
  const fill = $('#ring-fill');
  fill.style.strokeDasharray = String(circ);
  fill.style.strokeDashoffset = String(circ * (1-pct));
  $('#ring-label').textContent = Math.round(pct*100) + '%';
  $('#stats-count').textContent = `${totalKnown} / ${totalWords} palavras`;
  $('#stats-streak').textContent = streakText();
  $('#stat-line').textContent = `${TOPICS.length} tópicos · ${totalWords} palavras · PT → ${state.lang.toUpperCase()}`;
}
function updateContinueBanner(){
  const banner = $('#continue-banner');
  const ls = state.lastStudied;
  if(!ls){ banner.hidden = true; return; }
  const topic = TOPICS.find(t=>t.id===ls.topicId);
  if(!topic){ banner.hidden = true; return; }
  banner.hidden = false;
  $('#cb-emoji').textContent = topic.emoji;
  $('#cb-title').textContent = topic.name;
  banner.onclick = (e)=>{ e.preventDefault(); openCategory(ls.topicId); };
}
function topicFiltered(topic){
  if(filterState.text && !topic.name.toLowerCase().includes(filterState.text)) return false;
  const known = countKnown(topic.id);
  const total = topic.words.length;
  if(filterState.chip==='progress') return known>0 && known<total;
  if(filterState.chip==='done') return total>0 && known===total;
  if(filterState.chip==='new') return known===0;
  return true;
}
function renderHome(){
  updateStatsCard();
  updateContinueBanner();
  const grid = $('#topics');
  grid.innerHTML = '';
  const list = TOPICS.filter(topicFiltered);
  $('#empty-search').hidden = list.length > 0;
  list.forEach((topic) => {
    const known = countKnown(topic.id);
    const total = topic.words.length;
    const pct = total ? Math.round(known/total*100) : 0;
    const tile = document.createElement('button');
    tile.className = 'tile' + (known===total && total>0 ? ' done' : '');
    tile.type = 'button';
    tile.innerHTML = `
      <div class="emoji">${topic.emoji}</div>
      <div class="name">${topic.name}</div>
      <div class="meta"><span>${total} palavras</span><span class="known">${known} ✓</span></div>
      <div class="bar"><div class="bar-fill" style="width:${pct}%"></div></div>
    `;
    tile.addEventListener('click', () => openCategory(topic.id));
    grid.appendChild(tile);
  });
}

// =========================================================================
// STUDY
// =========================================================================
function openCategory(id){
  const topic = TOPICS.find(t=>t.id===id);
  if(!topic) return;
  state.currentCat = id;
  const idxs = topic.words.map((_,i)=>i);
  state.queue = state.order==='seq' ? idxs : shuffled(idxs);
  state.i = 0;
  state.revealed = false;
  state.sessionMissed = [];
  bumpStreak();
  $('#home').classList.add('off');
  $('#study').classList.add('on');
  $('#study-title').textContent = topic.name;
  renderCard();
}
function backHome(){
  state.currentCat = null;
  $('#study').classList.remove('on');
  $('#home').classList.remove('off');
  renderHome();
}
function currentWord(){
  const topic = TOPICS.find(t=>t.id===state.currentCat);
  if(!topic) return null;
  const idx = state.queue[state.i];
  return { topic, idx, word: topic.words[idx] };
}
function cueFor(){
  if(state.cue==='mix'){
    const r = Math.random();
    return r < .34 ? 'pt' : (r < .67 ? 'emoji' : 'foto');
  }
  return state.cue;
}

// Foto real via backend (proxy para Wikimedia Commons)
const photoCache = {};
async function fetchPhoto(query){
  if(query in photoCache) return photoCache[query];
  try{
    const res = await fetch(`${API_BASE}/api/image?q=${encodeURIComponent(query)}`);
    const json = await res.json();
    const result = json.found ? json : null;
    photoCache[query] = result;
    return result;
  }catch(_){
    return null;
  }
}
async function showPhoto(query){
  const wrap = $('#photo-wrap');
  const img = $('#photo-img');
  const credit = $('#photo-credit');
  const label = $('#cue-label');
  wrap.classList.add('on');
  img.removeAttribute('src');
  img.alt = '';
  credit.innerHTML = '<span class="photo-status">buscando foto…</span>';
  const requestedFor = state.i;
  const result = await fetchPhoto(query);
  if(state.i !== requestedFor) return;
  if(!result){
    wrap.classList.remove('on');
    label.textContent = 'Sem foto — tente outra palavra';
    return;
  }
  img.src = result.url;
  img.alt = result.title;
  credit.innerHTML = `<a href="${result.page}" target="_blank" rel="noopener">Wikimedia Commons</a>`;
}

function renderCard(){
  const cw = currentWord();
  const total = state.queue.length;
  $('#study-progress').textContent = `${Math.min(state.i+1,total)}/${total}`;
  if(state.i >= total){
    renderDone();
    return;
  }
  // Persist "continuar de onde parou" só quando já avançou pelo menos 1 carta
  if(state.i > 0){
    state.lastStudied = { topicId: state.currentCat, i: state.i };
    saveState();
  }
  const { pt, en, emoji } = cw.word;
  const cue = cueFor();
  const cueEl = $('#cue');
  const photoWrap = $('#photo-wrap');
  photoWrap.classList.remove('on');
  if(cue==='foto'){
    cueEl.classList.remove('emoji');
    cueEl.textContent = '';
    $('#cue-label').textContent = 'Que palavra é essa?';
    showPhoto(en.replace(/^to /,''));
  }else{
    cueEl.classList.toggle('emoji', cue==='emoji');
    cueEl.textContent = cue==='emoji' ? emoji : pt;
    $('#cue-label').textContent = cue==='emoji' ? 'Que palavra é essa?' : 'Traduza';
  }
  $('#answer-en').textContent = en;
  $('#answer-pt').textContent = pt;
  $('#answer-emoji').textContent = emoji;
  $('#answer').classList.remove('on');
  state.revealed = false;

  const nb = $('#notebook');
  nb.hidden = !state.notebook;
  $('#nb-input').value = '';
  $('#verdict').textContent = '';
  $('#verdict').className = 'verdict';
  if(state.notebook) setTimeout(()=>$('#nb-input').focus(), 60);

  renderControls();
}
function renderControls(){
  const wrap = $('#controls');
  if(!state.revealed){
    wrap.className = 'controls';
    wrap.innerHTML = `
      <button class="btn" id="reveal-btn">Revelar</button>
      <button class="btn primary" id="next-btn">Pular →</button>
    `;
    $('#reveal-btn').addEventListener('click', reveal);
    $('#next-btn').addEventListener('click', next);
  }else{
    wrap.className = 'controls full';
    wrap.innerHTML = `
      <button class="btn miss" id="miss-btn">Errei</button>
      <button class="btn gold" id="soso-btn">Quase</button>
      <button class="btn primary" id="know-btn">Sabia ✓</button>
    `;
    $('#miss-btn').addEventListener('click', ()=>markAndNext(false));
    $('#soso-btn').addEventListener('click', ()=>next());
    $('#know-btn').addEventListener('click', ()=>markAndNext(true));
  }
}
function reveal(){
  state.revealed = true;
  $('#answer').classList.add('on');
  if(state.notebook){
    const cw = currentWord();
    const v = matchAnswer($('#nb-input').value, cw.word.en);
    const el = $('#verdict');
    if(v==='ok'){ el.textContent = '✓ Perfeito.'; el.className='verdict ok'; }
    else if(v==='close'){ el.textContent = '≈ Quase — confira a grafia.'; el.className='verdict close'; }
    else if(v==='empty'){ el.textContent = 'Você não escreveu nada.'; el.className='verdict no'; }
    else { el.textContent = '✗ Não bateu.'; el.className='verdict no'; }
  }
  renderControls();
}
function markAndNext(known){
  const cw = currentWord();
  if(!cw) return;
  const topicId = cw.topic.id;
  state.known[topicId] = state.known[topicId] || {};
  if(known){
    state.known[topicId][cw.idx] = true;
  } else {
    delete state.known[topicId][cw.idx];
    if(!state.sessionMissed.some(m=>m.idx===cw.idx)) state.sessionMissed.push({ idx: cw.idx });
  }
  saveState();
  syncWord(topicId, cw.idx, known);
  next();
}
function next(){
  state.i++;
  state.revealed = false;
  renderCard();
}
function renderDone(){
  const topicId = state.currentCat;
  const known = countKnown(topicId);
  const topic = TOPICS.find(t=>t.id===topicId);
  const total = topic.words.length;
  const missedCount = state.sessionMissed.length;
  state.lastStudied = null;
  saveState();
  const wrap = $('#card');
  wrap.innerHTML = `
    <div class="done">
      <div style="font-size:44px">${missedCount ? '💪' : '🌱'}</div>
      <h3>Rodada completa.</h3>
      <p>Você marcou <b>${known}/${total}</b> como sabidas neste tópico${missedCount ? `, errou ${missedCount}` : ''}.</p>
    </div>
  `;
  const c = $('#controls');
  c.className = 'controls';
  const reviewBtn = missedCount ? `<button class="btn miss" id="review-btn">Revisar erros (${missedCount})</button>` : '';
  c.innerHTML = `
    ${reviewBtn}
    <button class="btn" id="again-btn">Repetir tópico</button>
    <button class="btn primary" id="home-btn">Outro tópico</button>
  `;
  if(missedCount){
    $('#review-btn').addEventListener('click', ()=>{
      state.queue = state.sessionMissed.map(m=>m.idx);
      state.sessionMissed = [];
      state.i = 0;
      state.revealed = false;
      renderCard();
    });
  }
  $('#again-btn').addEventListener('click', ()=>openCategory(topicId));
  $('#home-btn').addEventListener('click', backHome);
  $('#notebook').hidden = true;
}

// =========================================================================
// AUTH (Supabase) + SYNC
// =========================================================================
let sb = null;
let currentSession = null;

function initSupabase(){
  if(window.SUPABASE_URL && window.SUPABASE_ANON_KEY && window.supabase){
    sb = window.supabase.createClient(window.SUPABASE_URL, window.SUPABASE_ANON_KEY);
  }
}
async function restoreSession(){
  if(!sb) return;
  const { data } = await sb.auth.getSession();
  currentSession = data.session;
  updateAccountUI();
  sb.auth.onAuthStateChange((event, session) => {
    currentSession = session;
    updateAccountUI();
    if(event === 'SIGNED_IN') syncOnLogin();
  });
}
const ACCOUNT_ICON = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"></circle><path d="M4 20c0-4 3.5-7 8-7s8 3 8 7"></path></svg>';
function updateAccountButton(){
  const btn = $('#account-btn');
  if(currentSession && currentSession.user){
    btn.textContent = (currentSession.user.email||'?')[0].toUpperCase();
    btn.title = currentSession.user.email;
    btn.style.background = 'var(--accent-soft)';
    btn.style.color = 'var(--accent)';
    btn.style.borderColor = 'var(--accent)';
  }else{
    btn.innerHTML = ACCOUNT_ICON;
    btn.title = 'Entrar';
    btn.style.background = '';
    btn.style.color = '';
    btn.style.borderColor = '';
  }
}
function updateAccountUI(){
  updateAccountButton();
  const unavailable = $('#auth-unavailable');
  const signedOut = $('#auth-signed-out');
  const signedIn = $('#auth-signed-in');
  if(!sb){
    unavailable.hidden = false; signedOut.hidden = true; signedIn.hidden = true;
    return;
  }
  unavailable.hidden = true;
  if(currentSession && currentSession.user){
    signedOut.hidden = true; signedIn.hidden = false;
    const email = currentSession.user.email || '';
    $('#account-avatar').textContent = email[0] || '?';
    $('#account-email').textContent = email;
  }else{
    signedOut.hidden = false; signedIn.hidden = true;
  }
}
function syncWord(topicId, idx, known){
  if(!sb || !currentSession) return;
  fetch(`${API_BASE}/api/progress/${topicId}/${idx}?known=${known}`, {
    method:'POST',
    headers:{ Authorization:`Bearer ${currentSession.access_token}` },
  }).catch(()=>{});
}
async function syncOnLogin(){
  if(!currentSession) return;
  const token = currentSession.access_token;
  try{
    const res = await fetch(`${API_BASE}/api/progress`, { headers:{ Authorization:`Bearer ${token}` } });
    if(res.ok){
      const { items } = await res.json();
      items.forEach(it=>{
        state.known[it.topic_id] = state.known[it.topic_id] || {};
        state.known[it.topic_id][it.word_index] = true;
      });
    }
    const localItems = [];
    Object.entries(state.known).forEach(([topicId, words])=>{
      Object.keys(words).forEach(idx=>localItems.push({ topic_id: topicId, word_index: Number(idx) }));
    });
    if(localItems.length){
      await fetch(`${API_BASE}/api/progress/bulk`, {
        method:'POST',
        headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` },
        body: JSON.stringify({ items: localItems }),
      });
    }
    saveState();
    renderHome();
  }catch(_){ /* fica só local se a sync falhar */ }
}
function initAuthUI(){
  $('#account-btn').addEventListener('click', ()=>{ openSheet('account-sheet'); updateAccountUI(); });
  $('#account-close-1').addEventListener('click', closeSheet);
  $('#account-close-2').addEventListener('click', closeSheet);
  $('#auth-send').addEventListener('click', async ()=>{
    const email = $('#auth-email').value.trim();
    const statusEl = $('#auth-status');
    if(!email || !email.includes('@')){
      statusEl.textContent = 'Digite um e-mail válido.'; statusEl.className = 'auth-status err';
      return;
    }
    statusEl.textContent = 'Enviando…'; statusEl.className = 'auth-status';
    try{
      const { error } = await sb.auth.signInWithOtp({ email, options: { emailRedirectTo: window.location.href } });
      if(error){ statusEl.textContent = 'Erro: ' + error.message; statusEl.className = 'auth-status err'; }
      else { statusEl.textContent = 'Link enviado! Confira seu e-mail.'; statusEl.className = 'auth-status ok'; }
    }catch(e){
      statusEl.textContent = 'Não consegui enviar. Tente de novo.'; statusEl.className = 'auth-status err';
    }
  });
  $('#auth-signout').addEventListener('click', async ()=>{
    if(sb) await sb.auth.signOut();
    closeSheet();
  });
}

// =========================================================================
// SETTINGS + THEME + SHEETS
// =========================================================================
function applyTheme(){
  if(state.theme==='auto') document.documentElement.removeAttribute('data-theme');
  else document.documentElement.setAttribute('data-theme', state.theme);
  const dark = state.theme==='dark' || (state.theme==='auto' && matchMedia('(prefers-color-scheme: dark)').matches);
  $('#theme-btn').textContent = dark ? '☀' : '☾';
}
function openSheet(id){
  $$('.sheet').forEach(s=>s.classList.remove('on'));
  $('#'+id).classList.add('on');
  $('#scrim').classList.add('on');
}
function closeSheet(){
  $('#scrim').classList.remove('on');
  $$('.sheet').forEach(s=>s.classList.remove('on'));
}

function bindSeg(sel, key, cb){
  $$(sel + ' button').forEach(b=>{
    b.addEventListener('click', ()=>{
      if(b.disabled) return;
      $$(sel + ' button').forEach(x=>x.classList.remove('on'));
      b.classList.add('on');
      cb(b.dataset[key]);
      saveState();
    });
  });
}
function initSegs(){
  bindSeg('#lang-seg','lang', v=>{ state.lang=v; renderHome(); });
  bindSeg('#nb-seg','nb', v=>{ state.notebook = v==='on'; if(state.currentCat) renderCard(); });
  bindSeg('#order-seg','order', v=>{ state.order=v; });
  bindSeg('#theme-seg','th', v=>{ state.theme=v; applyTheme(); });
  const setSeg = (sel, attr, val) => {
    $$(sel + ' button').forEach(b=>{ b.classList.toggle('on', b.dataset[attr]===val); });
  };
  setSeg('#lang-seg','lang', state.lang);
  setSeg('#nb-seg','nb', state.notebook?'on':'off');
  setSeg('#order-seg','order', state.order);
  setSeg('#theme-seg','th', state.theme);
}
function initModebar(){
  $$('.modebar button').forEach(b=>{
    b.addEventListener('click', ()=>{
      $$('.modebar button').forEach(x=>x.classList.remove('on'));
      b.classList.add('on');
      state.cue = b.dataset.cue;
      saveState();
      if(state.currentCat) renderCard();
    });
  });
  $$('.modebar button').forEach(b=>b.classList.toggle('on', b.dataset.cue===state.cue));
}
function initSearchAndFilters(){
  $('#search-input').addEventListener('input', (e)=>{
    filterState.text = e.target.value.trim().toLowerCase();
    renderHome();
  });
  $$('#filter-row button').forEach(b=>{
    b.addEventListener('click', ()=>{
      $$('#filter-row button').forEach(x=>x.classList.remove('on'));
      b.classList.add('on');
      filterState.chip = b.dataset.filter;
      renderHome();
    });
  });
}

// =========================================================================
// BOOT
// =========================================================================
async function init(){
  loadState();
  applyTheme();
  initSupabase();
  try{
    await loadTopics();
  }catch(e){
    $('#stat-line').textContent = 'Não consegui falar com o servidor. Ele está rodando?';
    return;
  }
  renderHome();
  initModebar();
  initSegs();
  initSearchAndFilters();
  initAuthUI();
  restoreSession();

  $('#back-btn').addEventListener('click', backHome);
  $('#settings-btn').addEventListener('click', ()=>openSheet('sheet'));
  $('#sheet-close').addEventListener('click', closeSheet);
  $('#scrim').addEventListener('click', closeSheet);
  $('#theme-btn').addEventListener('click', ()=>{
    const order = ['auto','light','dark'];
    const i = order.indexOf(state.theme);
    state.theme = order[(i+1) % order.length];
    $$('#theme-seg button').forEach(b=>b.classList.toggle('on', b.dataset.th===state.theme));
    applyTheme(); saveState();
  });

  $('#nb-input').addEventListener('keydown', (e)=>{
    if(e.key==='Enter'){
      if(!state.revealed) reveal();
      else next();
    }
  });

  document.addEventListener('keydown', (e)=>{
    if(!$('#study').classList.contains('on')) return;
    if(e.target.tagName === 'INPUT') return;
    if(e.key===' '){ e.preventDefault(); state.revealed ? next() : reveal(); }
    if(e.key==='ArrowRight') next();
    if(e.key==='1' && state.revealed) markAndNext(false);
    if(e.key==='3' && state.revealed) markAndNext(true);
  });

  matchMedia('(prefers-color-scheme: dark)').addEventListener?.('change', ()=>{
    if(state.theme==='auto') applyTheme();
  });
}
init();
