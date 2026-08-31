(function(){
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => document.querySelectorAll(s);
  const rand = (n) => Math.floor(Math.random()*n);
  function shuffled(arr){
    const a = arr.slice();
    for(let i=a.length-1;i>0;i--){ const j=rand(i+1); [a[i],a[j]]=[a[j],a[i]]; }
    return a;
  }
  function fold(s){
    return (s||'').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'').replace(/[^a-z0-9 ']/g,'').trim();
  }
  function levenshtein(a,b){
    if(a===b) return 0;
    if(!a.length) return b.length;
    if(!b.length) return a.length;
    const v0 = new Array(b.length+1), v1 = new Array(b.length+1);
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
    const b2 = b.replace(/^to /,''), a2 = a.replace(/^to /,'');
    if(a2 === b2) return 'ok';
    const d = Math.min(levenshtein(a,b), levenshtein(a2,b2));
    const len = Math.max(b.length, 4);
    if(d <= 1 || d/len < 0.18) return 'close';
    return 'no';
  }

  const LS_KEY = 'idiomas.study-prefs';
  let prefs = { cue:'pt', order:'rand', onlyUnknown:false };
  try{ Object.assign(prefs, JSON.parse(localStorage.getItem(LS_KEY)||'{}')); }catch(_){}
  function savePrefs(){ localStorage.setItem(LS_KEY, JSON.stringify(prefs)); }

  const WORDS = window.WORDS; // [{id,pt,en}]
  const known = new Set(window.KNOWN_IDS);
  const st = { queue: [], i: 0, revealed: false, sessionMissed: [] };

  function updateScopeCount(){
    const remaining = WORDS.filter(w=>!known.has(w.id)).length;
    $('#scope-count').textContent = remaining;
  }

  function buildQueue(){
    updateScopeCount();
    let idxs = WORDS.map((_,i)=>i);
    if(prefs.onlyUnknown){
      const filtered = idxs.filter(i=>!known.has(WORDS[i].id));
      if(filtered.length) idxs = filtered; // se já sabe tudo, cai de volta pro tópico inteiro
    }
    st.queue = prefs.order==='seq' ? idxs : shuffled(idxs);
    st.i = 0;
  }
  function currentWord(){ return WORDS[st.queue[st.i]]; }
  function cueFor(){
    if(prefs.cue==='mix') return Math.random() < .5 ? 'pt' : 'foto';
    return prefs.cue;
  }

  // Foto de capa da Wikipedia — algumas palavras (verbos, preposições,
  // conceitos abstratos) simplesmente não têm uma foto que faça sentido.
  // Quando isso acontece, caímos de volta pra palavra em texto sem alarde.
  const photoCache = {};
  async function fetchPhoto(query){
    if(query in photoCache) return photoCache[query];
    try{
      const res = await fetch(`${window.IMAGE_URL}?q=${encodeURIComponent(query)}`);
      const json = await res.json();
      const result = json.found ? json : null;
      photoCache[query] = result;
      return result;
    }catch(_){ return null; }
  }
  function showAsText(w){
    $('#photo-wrap').classList.remove('on');
    const cueEl = $('#cue');
    cueEl.textContent = w.pt;
    $('#cue-label').textContent = 'Traduza';
  }
  async function showPhoto(w){
    const wrap = $('#photo-wrap'), img = $('#photo-img'), credit = $('#photo-credit'), cueEl = $('#cue');
    wrap.classList.add('on');
    cueEl.textContent = '';
    img.removeAttribute('src'); img.alt = '';
    credit.innerHTML = '<span class="photo-status">buscando foto…</span>';
    $('#cue-label').textContent = 'Que palavra é essa?';
    const requestedFor = st.i;
    const result = await fetchPhoto(w.en.replace(/^to /,''));
    if(st.i !== requestedFor) return;
    if(!result){ showAsText(w); return; }
    img.src = result.url; img.alt = result.title;
    credit.innerHTML = `<a href="${result.page}" target="_blank" rel="noopener">Wikipedia</a>`;
  }

  function renderCard(){
    const total = st.queue.length;
    $('#study-progress').textContent = `${Math.min(st.i+1,total)}/${total}`;
    if(st.i >= total){ renderDone(); return; }
    const w = currentWord();
    const cue = cueFor();
    if(cue==='foto') showPhoto(w);
    else showAsText(w);

    $('#answer-en').textContent = w.en;
    $('#answer-pt').textContent = w.pt;
    $('#answer').classList.remove('on');
    st.revealed = false;

    $('#nb-input').value = '';
    $('#verdict').textContent = '';
    $('#verdict').className = 'verdict';
    setTimeout(()=>$('#nb-input').focus(), 60);

    renderControls();
  }
  function renderControls(){
    const wrap = $('#controls');
    if(!st.revealed){
      wrap.className = 'controls';
      wrap.innerHTML = `<button class="btn" id="reveal-btn">Revelar</button><button class="btn primary" id="next-btn">Pular →</button>`;
      $('#reveal-btn').addEventListener('click', reveal);
      $('#next-btn').addEventListener('click', next);
    }else{
      wrap.className = 'controls full';
      wrap.innerHTML = `<button class="btn miss" id="miss-btn">Errei</button><button class="btn gold" id="soso-btn">Quase</button><button class="btn primary" id="know-btn">Sabia ✓</button>`;
      $('#miss-btn').addEventListener('click', ()=>markAndNext(false));
      $('#soso-btn').addEventListener('click', ()=>next());
      $('#know-btn').addEventListener('click', ()=>markAndNext(true));
    }
  }
  function reveal(){
    st.revealed = true;
    $('#answer').classList.add('on');
    const w = currentWord();
    const v = matchAnswer($('#nb-input').value, w.en);
    const el = $('#verdict');
    if(v==='ok'){ el.textContent = '✓ Perfeito.'; el.className='verdict ok'; }
    else if(v==='close'){ el.textContent = '≈ Quase — confira a grafia.'; el.className='verdict close'; }
    else if(v==='empty'){ el.textContent = 'Você não escreveu nada.'; el.className='verdict no'; }
    else { el.textContent = '✗ Não bateu.'; el.className='verdict no'; }
    renderControls();
  }
  function syncWord(wordId, isKnown){
    fetch(`${window.MARK_URL_BASE}${wordId}/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': window.CSRF_TOKEN, 'Content-Type': 'application/x-www-form-urlencoded' },
      body: `known=${isKnown}`,
    }).catch(()=>{});
  }
  function markAndNext(isKnown){
    const w = currentWord();
    if(!w) return;
    if(isKnown) known.add(w.id);
    else{
      known.delete(w.id);
      if(!st.sessionMissed.includes(w.id)) st.sessionMissed.push(w.id);
    }
    syncWord(w.id, isKnown);
    updateScopeCount();
    next();
  }
  function next(){ st.i++; st.revealed = false; renderCard(); }

  function renderDone(){
    const knownCount = WORDS.filter(w=>known.has(w.id)).length;
    const missedCount = st.sessionMissed.length;
    const wrap = $('#card');
    wrap.innerHTML = `
      <div class="done">
        <div style="font-size:44px">${missedCount ? '💪' : '🌱'}</div>
        <h3>Rodada completa.</h3>
        <p>Você marcou <b>${knownCount}/${WORDS.length}</b> como sabidas neste tópico${missedCount ? `, errou ${missedCount}` : ''}.</p>
      </div>
    `;
    const c = $('#controls');
    c.className = 'controls';
    const reviewBtn = missedCount ? `<button class="btn miss" id="review-btn">Revisar erros (${missedCount})</button>` : '';
    c.innerHTML = `${reviewBtn}<button class="btn" id="again-btn">Repetir tópico</button><a class="btn primary" id="home-btn" href="${window.HOME_URL}">Outro tópico</a>`;
    if(missedCount){
      $('#review-btn').addEventListener('click', ()=>{
        const missedSet = new Set(st.sessionMissed);
        st.queue = WORDS.map((w,i)=>i).filter(i=>missedSet.has(WORDS[i].id));
        st.sessionMissed = []; st.i = 0; st.revealed = false;
        renderCard();
      });
    }
    $('#again-btn').addEventListener('click', ()=>{ buildQueue(); renderCard(); });
    $('#notebook').style.display = 'none';
  }

  function initModebar(){
    $$('.modebar button').forEach(b=>{
      b.classList.toggle('on', b.dataset.cue===prefs.cue);
      b.addEventListener('click', ()=>{
        $$('.modebar button').forEach(x=>x.classList.remove('on'));
        b.classList.add('on');
        prefs.cue = b.dataset.cue;
        savePrefs();
        renderCard();
      });
    });
  }
  function initScopeToggle(){
    const input = $('#scope-input');
    input.checked = prefs.onlyUnknown;
    input.addEventListener('change', ()=>{
      prefs.onlyUnknown = input.checked;
      savePrefs();
      buildQueue();
      renderCard();
    });
  }

  $('#nb-input')?.addEventListener('keydown', (e)=>{
    if(e.key==='Enter'){ st.revealed ? next() : reveal(); }
  });
  document.addEventListener('keydown', (e)=>{
    if(e.target.tagName === 'INPUT') return;
    if(e.key===' '){ e.preventDefault(); st.revealed ? next() : reveal(); }
    if(e.key==='ArrowRight') next();
    if(e.key==='1' && st.revealed) markAndNext(false);
    if(e.key==='3' && st.revealed) markAndNext(true);
  });

  buildQueue();
  initModebar();
  initScopeToggle();
  renderCard();
})();
