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
  let prefs = { cue:'pt', order:'rand' };
  try{ Object.assign(prefs, JSON.parse(localStorage.getItem(LS_KEY)||'{}')); }catch(_){}
  // este tópico pode não ter nenhuma palavra fotografável (ex: preposições) —
  // nesse caso a aba "Foto" nem existe no HTML, então ignoramos qualquer
  // preferência antiga de outro tópico que ainda apontasse pra ela.
  if(!window.TOPIC_HAS_PHOTO) prefs.cue = 'pt';
  function savePrefs(){ localStorage.setItem(LS_KEY, JSON.stringify(prefs)); }

  const ALL_WORDS = window.WORDS || []; // [{id,pt,en,has_photo,photo_url,photo_page,due,last_wrong}]
  const WORDS = ALL_WORDS.filter(w => w.due); // só o que está vencido ou é novo entra na sessão
  const st = { queue: [], i: 0, revealed: false, sessionMissed: [], sessionAnswers: [] };

  function buildQueue(){
    const idxs = WORDS.map((_,i)=>i);
    st.queue = prefs.order==='seq' ? idxs : shuffled(idxs);
    st.i = 0;
  }
  function currentWord(){ return WORDS[st.queue[st.i]]; }

  const photoCache = {};
  async function fetchPhotoLive(query){
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
  function paintPhoto(url, title, page, credit){
    const img = $('#photo-img'), creditEl = $('#photo-credit');
    img.src = url; img.alt = title || '';
    creditEl.innerHTML = page
      ? `<a href="${page}" target="_blank" rel="noopener">${credit || 'fonte'}</a>`
      : (credit || '');
  }
  // Escolhe uma foto aleatória entre as variantes cadastradas — assim a
  // mesma palavra não mostra sempre a mesma imagem. Guarda o índice escolhido
  // por sessão pra não repetir a mesma foto se a palavra voltar em Revisar.
  const seenVariant = {};
  function pickVariant(w){
    const vs = w.photo_variants;
    if(!vs || !vs.length){
      return w.photo_url ? {url:w.photo_url, page:w.photo_page, credit:w.photo_credit} : null;
    }
    let idx = rand(vs.length);
    // se já foi visto e tem mais de uma opção, tenta a próxima
    if(vs.length > 1 && seenVariant[w.id] === idx) idx = (idx + 1) % vs.length;
    seenVariant[w.id] = idx;
    return vs[idx];
  }
  async function showPhoto(w){
    const wrap = $('#photo-wrap'), img = $('#photo-img'), credit = $('#photo-credit'), cueEl = $('#cue');
    wrap.classList.add('on');
    cueEl.textContent = '';
    $('#cue-label').textContent = 'Que palavra é essa?';
    // foto já veio pronta do servidor (populada pelo check_photos) — sem round-trip
    const chosen = pickVariant(w);
    if(chosen){
      img.src = chosen.url; img.alt = w.en;
      credit.innerHTML = chosen.page
        ? `<a href="${chosen.page}" target="_blank" rel="noopener">${chosen.credit || 'fonte'}</a>`
        : (chosen.credit || '');
      return;
    }
    // fallback: busca ao vivo (palavra ainda não passou pelo check_photos)
    img.removeAttribute('src'); img.alt = '';
    credit.innerHTML = '<span class="photo-status">buscando foto…</span>';
    const requestedFor = st.i;
    const result = await fetchPhotoLive(w.en.replace(/^to /,''));
    if(st.i !== requestedFor) return;
    if(!result){ showAsText(w); return; }
    paintPhoto(result.url, result.title, result.page, result.credit);
  }

  function renderCard(){
    const total = st.queue.length;
    $('#study-progress').textContent = `${Math.min(st.i+1,total)}/${total}`;
    if(st.i >= total){ renderDone(); return; }
    const w = currentWord();
    if(prefs.cue==='foto' && w.has_photo) showPhoto(w);
    else showAsText(w);

    $('#answer-en').textContent = w.en;
    $('#answer-pt').textContent = w.pt;
    $('#answer').classList.remove('on');
    st.revealed = false;

    const lastWrongEl = $('#last-wrong');
    if(w.last_wrong){
      lastWrongEl.hidden = false;
      lastWrongEl.textContent = `Da última vez você escreveu "${w.last_wrong}" — repare na grafia.`;
    }else{
      lastWrongEl.hidden = true;
    }

    $('#nb-input').value = '';
    $('#verdict').textContent = '';
    $('#verdict').className = 'verdict';
    setTimeout(()=>$('#nb-input').focus(), 60);

    renderControls();
  }
  function renderControls(){
    const wrap = $('#controls');
    if(!st.revealed){
      // Dois caminhos, propositais: "Conferir" (só quando escreveu algo,
      // pra proteger o recall ativo) e "Não lembro" (assume miss sem
      // fingir esforço). Antes o Conferir vazio revelava a resposta —
      // quebra o objetivo do app.
      wrap.className = 'controls';
      wrap.innerHTML = `
        <button class="btn" id="giveup-btn">Não lembro</button>
        <button class="btn primary" id="reveal-btn" disabled>Conferir <kbd>Enter</kbd></button>`;
      $('#giveup-btn').addEventListener('click', ()=>reveal({giveup:true}));
      $('#reveal-btn').addEventListener('click', ()=>reveal());
      updateConferirState();
    }else{
      wrap.className = 'controls single';
      wrap.innerHTML = `<button class="btn primary" id="next-btn">Continuar <kbd>Enter</kbd></button>`;
      $('#next-btn').addEventListener('click', next);
    }
  }
  function updateConferirState(){
    const btn = $('#reveal-btn');
    if(!btn) return;
    const hasText = $('#nb-input').value.trim().length > 0;
    btn.disabled = !hasText;
  }
  // O sistema decide o resultado a partir do que foi digitado (recall
  // ativo) OU do botão "Não lembro" (giveup). Nunca revela a resposta
  // sem alguma dessas duas coisas — antes hitting Enter vazio ja mostrava.
  function reveal(opts){
    opts = opts || {};
    const typed = $('#nb-input').value.trim();
    // Botão Conferir só existe se digitou algo (o listener atualiza
    // .disabled). Chamado sem giveup e sem texto = ignorar (não revelar).
    if(!opts.giveup && !typed) return;
    st.revealed = true;
    $('#answer').classList.add('on');
    const w = currentWord();
    const el = $('#verdict');
    let result;
    if(opts.giveup){
      el.textContent = '↻ Sem problema — memoriza aí pra próxima.';
      el.className = 'verdict no';
      result = 'miss';
    }else{
      const v = matchAnswer(typed, w.en);
      if(v==='ok'){ el.textContent = '✓ Perfeito.'; el.className='verdict ok'; result='know'; }
      else if(v==='close'){ el.textContent = '≈ Quase — confira a grafia.'; el.className='verdict close'; result='soso'; }
      else { el.textContent = '✗ Não bateu.'; el.className='verdict no'; result='miss'; }
    }
    if(result==='miss' && !st.sessionMissed.includes(w.id)) st.sessionMissed.push(w.id);
    st.sessionAnswers.push({wordId:w.id, pt:w.pt, en:w.en, typed, result});
    syncWord(w.id, result, result==='miss' ? typed : '');
    renderControls();
  }
  function syncWord(wordId, result, wrongAnswer){
    return fetch(`${window.MARK_URL_BASE}${wordId}/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': window.CSRF_TOKEN, 'Content-Type': 'application/x-www-form-urlencoded' },
      body: `result=${result}&wrong_answer=${encodeURIComponent(wrongAnswer||'')}`,
    }).catch(()=>{});
  }
  function next(){ st.i++; st.revealed = false; renderCard(); }

  function renderDone(){
    const missedCount = st.sessionMissed.length;
    const total = WORDS.length;
    const rightCount = total - missedCount;
    const pct = total ? Math.round(rightCount / total * 100) : 0;
    const wrap = $('#card');
    wrap.innerHTML = `
      <div class="done">
        <div class="done-label">Rodada completa</div>
        <div class="done-score"><b>${rightCount}</b> <span class="done-slash">/</span> ${total} <span class="done-pct">${pct}%</span></div>
        <p class="done-sub">${missedCount ? `${missedCount} ${missedCount===1?'palavra pra revisar':'palavras pra revisar'} agora.` : 'Perfeito. Volte amanhã pra próxima rodada.'}</p>
        <div class="coach-slot" id="coach-slot" hidden>
          <div class="coach-label">Seu coach</div>
          <p class="coach-msg" id="coach-msg"></p>
        </div>
      </div>
    `;
    const c = $('#controls');
    c.className = 'controls';
    const reviewBtn = missedCount ? `<button class="btn miss" id="review-btn">Revisar erros (${missedCount})</button>` : '';
    c.innerHTML = `${reviewBtn}<a class="btn primary" id="home-btn" href="${window.HOME_URL}">Voltar aos tópicos</a>`;
    if(missedCount){
      $('#review-btn').addEventListener('click', ()=>{
        const missedSet = new Set(st.sessionMissed);
        st.queue = WORDS.map((w,i)=>i).filter(i=>missedSet.has(WORDS[i].id));
        st.sessionMissed = []; st.i = 0; st.revealed = false;
        renderCard();
      });
    }
    $('#notebook').style.display = 'none';
    requestCoach();
  }
  async function requestCoach(){
    if(!st.sessionAnswers.length) return;
    const slot = $('#coach-slot');
    if(!slot) return;
    slot.hidden = false;
    $('#coach-msg').innerHTML = '<span class="photo-status">pensando…</span>';
    try{
      const res = await fetch(window.COACH_URL, {
        method: 'POST',
        headers: {'X-CSRFToken': window.CSRF_TOKEN, 'Content-Type': 'application/json'},
        body: JSON.stringify({topic: window.TOPIC_NAME, answers: st.sessionAnswers}),
      });
      const json = await res.json();
      if(!json.enabled){ slot.hidden = true; return; }
      if(!json.message){
        $('#coach-msg').textContent = 'Sem comentário desta vez.';
        return;
      }
      $('#coach-msg').textContent = json.message;
    }catch(_){
      slot.hidden = true;
    }
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

  $('#nb-input')?.addEventListener('input', updateConferirState);
  $('#nb-input')?.addEventListener('keydown', (e)=>{
    if(e.key==='Enter'){
      if(st.revealed){ next(); return; }
      const typed = e.target.value.trim();
      if(typed) reveal();
      // Enter vazio: nada acontece (protege recall ativo)
    }
  });
  document.addEventListener('keydown', (e)=>{
    if(e.target.tagName === 'INPUT') return;
    // Fora do input: espaço só avança se já revelou. Nunca revela nada
    // sem input digitado.
    if(e.key===' ' && st.revealed){ e.preventDefault(); next(); }
    if(e.key==='ArrowRight' && st.revealed) next();
  });

  if(WORDS.length){
    buildQueue();
    initModebar();
    renderCard();
  }
})();
