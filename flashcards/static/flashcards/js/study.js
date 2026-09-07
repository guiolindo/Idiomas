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
  // Diff caractere-a-caractere entre a resposta digitada e a esperada.
  // Devolve HTML com spans: letras certas em tinta, erradas em vermelho,
  // faltantes sublinhadas. Alinhamento simples baseado em LCS aproximado —
  // não é diff perfeito de Myers, mas é O(n·m) rápido pro tamanho de
  // palavras aqui (< 30 chars) e produz feedback intuitivo.
  function escapeHtml(s){
    return s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }
  function buildDiff(typed, target){
    const a = fold(typed), b = fold(target);
    if(!a) return `<span class="d-miss">${escapeHtml(target)}</span>`;
    // Programação dinâmica pra tabela LCS
    const m = a.length, n = b.length;
    const dp = Array.from({length:m+1}, () => new Array(n+1).fill(0));
    for(let i=1;i<=m;i++) for(let j=1;j<=n;j++){
      dp[i][j] = a[i-1]===b[j-1] ? dp[i-1][j-1]+1 : Math.max(dp[i-1][j], dp[i][j-1]);
    }
    // Backtrack pra montar as sequências alinhadas
    const parts = [];
    let i=m, j=n;
    while(i>0 && j>0){
      if(a[i-1]===b[j-1]){ parts.unshift({t:'ok', c:b[j-1]}); i--; j--; }
      else if(dp[i-1][j] >= dp[i][j-1]){ parts.unshift({t:'extra', c:a[i-1]}); i--; }
      else { parts.unshift({t:'miss', c:b[j-1]}); j--; }
    }
    while(i>0){ parts.unshift({t:'extra', c:a[--i]+''}); }
    while(j>0){ parts.unshift({t:'miss', c:b[--j]+''}); }
    // Junta caracteres consecutivos do mesmo tipo em spans
    let html = '', prev = null, buf = '';
    parts.forEach(p => {
      if(p.t !== prev){
        if(buf) html += `<span class="d-${prev}">${escapeHtml(buf)}</span>`;
        buf = p.c; prev = p.t;
      } else { buf += p.c; }
    });
    if(buf) html += `<span class="d-${prev}">${escapeHtml(buf)}</span>`;
    return html;
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
  let prefs = { cue:'pt', order:'rand', voice:false };
  try{ Object.assign(prefs, JSON.parse(localStorage.getItem(LS_KEY)||'{}')); }catch(_){}
  // este tópico pode não ter nenhuma palavra fotografável (ex: preposições) —
  // nesse caso a aba "Foto" nem existe no HTML, então ignoramos qualquer
  // preferência antiga de outro tópico que ainda apontasse pra ela.
  if(!window.TOPIC_HAS_PHOTO && prefs.cue === 'foto') prefs.cue = 'pt';
  // Modo de estudo (escolhido antes da sessão) trava algumas prefs:
  //   ditado → cue sempre 'ditado' (não alterna PT/Foto)
  //   voz    → cue livre entre PT/Foto, mas voice=true fixo
  //   escrita → PT/Foto alternável, voice=false
  // Isso evita que o localStorage de uma sessão anterior misture com o
  // modo atual (ex: entrar em "Voz" com prefs.cue='ditado' salvo).
  const STUDY_MODE = window.STUDY_MODE || 'escrita';
  // Ambos ditado e transcricao apresentam o cartao do mesmo jeito (audio +
  // botao "Ouvir de novo"), a diferenca esta so no ALVO da resposta:
  //   - ditado      → aluno escreve em português (w.pt)
  //   - transcricao → aluno escreve em inglês (w.en)  ← spelling training
  if(STUDY_MODE === 'ditado' || STUDY_MODE === 'transcricao'){
    prefs.cue = STUDY_MODE;  // usa o proprio nome como cue
    prefs.voice = false;
  }
  else if(STUDY_MODE === 'voz'){ prefs.voice = true; if(prefs.cue === 'ditado' || prefs.cue === 'transcricao') prefs.cue = 'pt'; }
  else { prefs.voice = false; if(prefs.cue === 'ditado' || prefs.cue === 'transcricao') prefs.cue = 'pt'; }
  function savePrefs(){ localStorage.setItem(LS_KEY, JSON.stringify(prefs)); }

  const ALL_WORDS = window.WORDS || []; // [{id,pt,en,has_photo,photo_url,photo_page,due,last_wrong}]
  const WORDS = ALL_WORDS.filter(w => w.due); // só o que está vencido ou é novo entra na sessão
  const st = { queue: [], i: 0, revealed: false, sessionMissed: [], sessionAnswers: [] };
  // guarda o HTML original do card e do notebook — o done screen substitui
  // o innerHTML do card, então precisamos restaurar antes de rodar uma
  // rodada de revisão (senão renderCard atualiza elementos que não existem
  // mais e a tela quebra).
  const ORIGINAL_CARD_HTML = $('#card')?.innerHTML || '';

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
    cueEl.classList.remove('dictation');
    $('#cue-label').textContent = 'Traduza';
  }
  // Áudio como estímulo — dois modos possíveis:
  //   - ditado:      COMPREENSÃO (múltipla escolha PT) — reformulado
  //                  por recomendação de SLA. Antes pedia pra ESCREVER
  //                  em PT, virava teste de ortografia PT + tradução,
  //                  não compreensão auditiva.
  //   - transcricao: escute e escreva em INGLÊS (spelling training)
  function showAsDictation(w){
    $('#photo-wrap').classList.remove('on');
    const cueEl = $('#cue');
    cueEl.innerHTML = '<button type="button" class="dictation-btn" id="dictation-play" aria-label="Ouvir">🔊 Ouvir de novo</button>';
    cueEl.classList.add('dictation');
    const label = prefs.cue === 'transcricao'
      ? 'Escute e escreva o que ouviu em inglês'
      : 'Escute e escolha o significado';
    $('#cue-label').textContent = label;
    const play = () => speak(w.en);
    setTimeout(play, 250);
    $('#dictation-play')?.addEventListener('click', play);
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
    if(prefs.cue==='ditado' || prefs.cue==='transcricao') showAsDictation(w);
    else if(prefs.cue==='foto' && w.has_photo) showPhoto(w);
    else showAsText(w);

    $('#answer-en').textContent = w.en;
    $('#answer-pt').textContent = w.pt;
    $('#answer').classList.remove('on');
    st.revealed = false;

    // Palavra travada (leech): 3+ erros seguidos. Aviso pequeno pro aluno
    // saber que essa é a "vilã" dele e vale gastar um segundo a mais
    // pensando — sem mudar o fluxo.
    const leechEl = $('#leech-badge');
    if(leechEl){ leechEl.hidden = !w.is_leech; }

    // "Da última vez você escreveu X" — só reaparece no MESMO idioma
    // em que foi errada. Antes, a dica vazava entre modos: erro em
    // "people" (modo Escrita) aparecia depois na tentativa "pessoa"
    // (modo Ditado) e confundia. Agora comparamos o idioma esperado da
    // resposta com o last_wrong_lang salvo.
    const currentLang = prefs.cue === 'ditado' ? 'pt' : 'en';
    const lastWrongEl = $('#last-wrong');
    const showLastWrong = w.last_wrong && (!w.last_wrong_lang || w.last_wrong_lang === currentLang);
    if(showLastWrong){
      lastWrongEl.hidden = false;
      lastWrongEl.textContent = `Da última vez você escreveu "${w.last_wrong}" — repare na grafia.`;
    }else{
      lastWrongEl.hidden = true;
    }

    $('#nb-input').value = '';
    $('#verdict').textContent = '';
    $('#verdict').className = 'verdict';
    // Se está no modo voz, o input está oculto — não focar (evita teclado
    // subir no mobile). Limpa o painel de voz também.
    if(prefs.voice){
      const heard = $('#voice-heard'); if(heard) heard.textContent = '';
      const hint = $('#voice-hint'); if(hint) hint.textContent = 'Clique no microfone e diga a palavra em inglês';
      voiceFailCount = 0;
    }else{
      // preventScroll evita o pulo pro topo/pro input quando trocamos de
      // aba (modebar) ou re-renderizamos por qualquer motivo. O cursor
      // ainda vai pro input, só sem o navegador rolar a página.
      setTimeout(()=>$('#nb-input').focus({preventScroll:true}), 60);
    }

    renderControls();
  }
  function renderControls(){
    const wrap = $('#controls');
    // Modo Compreensão (ditado): múltipla escolha, esconde notebook.
    if(prefs.cue === 'ditado' && !st.revealed){
      const w = currentWord();
      const options = shuffled([w.pt, ...(w.distractors || []).slice(0, 2)]);
      const notebook = $('#notebook');
      if(notebook) notebook.style.display = 'none';
      wrap.className = 'controls choice-grid';
      wrap.innerHTML = options.map((opt, i) =>
        `<button type="button" class="btn choice-btn" data-choice="${escapeHtml(opt)}">${escapeHtml(opt)}</button>`
      ).join('');
      $$('.choice-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          const picked = btn.dataset.choice;
          const correct = picked === w.pt;
          // Marca a que foi clicada + destaca a correta se errou
          $$('.choice-btn').forEach(b => {
            b.disabled = true;
            if(b.dataset.choice === w.pt) b.classList.add('right');
            else if(b === btn && !correct) b.classList.add('wrong');
          });
          st.revealed = true;
          $('#answer').classList.add('on');
          const el = $('#verdict');
          const result = correct ? 'know' : 'miss';
          if(correct){ el.innerHTML = '<span class="verdict-mark ok">✓</span> Certo.'; el.className = 'verdict ok'; }
          else { el.innerHTML = `<span class="verdict-mark no">✗</span> Era <b>${escapeHtml(w.pt)}</b>.`; el.className = 'verdict no'; }
          if(result==='miss' && !st.sessionMissed.includes(w.id)) st.sessionMissed.push(w.id);
          st.sessionAnswers.push({wordId:w.id, pt:w.pt, en:w.en, answer:picked, result});
          syncWord(w.id, result, result==='miss' ? picked : '');
          speak(w.en);
          setTimeout(() => {
            wrap.className = 'controls single';
            wrap.innerHTML = `<button class="btn primary" id="next-btn">Continuar <kbd>Enter</kbd></button>`;
            $('#next-btn').addEventListener('click', next);
          }, 900);
        });
      });
      return;
    }
    if(!st.revealed){
      // Dois caminhos, propositais: "Conferir" (só quando escreveu algo,
      // pra proteger o recall ativo) e "Não lembro" (assume miss sem
      // fingir esforço). Antes o Conferir vazio revelava a resposta —
      // quebra o objetivo do app.
      // Restaura notebook (caso volta de modo compreensão numa rodada)
      const nb = $('#notebook'); if(nb) nb.style.display = '';
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
  // ============ TTS (Web Speech API) ============
  // Sem servidor, sem arquivo permanente — o próprio navegador sintetiza
  // a fala. Zero custo, zero storage. Falha silenciosa em navegadores
  // que não suportam (raríssimo hoje).
  const TARGET_LANG = window.TARGET_LANG || 'en-US';
  let cachedVoice = null;
  function pickVoice(){
    if(cachedVoice) return cachedVoice;
    if(!window.speechSynthesis) return null;
    const voices = speechSynthesis.getVoices();
    if(!voices.length) return null;
    // Preferência: voz nativa do idioma alvo, priorizando "Google" ou
    // "Microsoft" (qualidade neural) sobre a voz padrão do sistema.
    const langPrefix = TARGET_LANG.split('-')[0];
    const matches = voices.filter(v => v.lang.startsWith(langPrefix));
    if(!matches.length) return null;
    cachedVoice = matches.find(v => /google/i.test(v.name)) ||
                  matches.find(v => /microsoft/i.test(v.name)) ||
                  matches.find(v => v.lang === TARGET_LANG) ||
                  matches[0];
    return cachedVoice;
  }
  function speak(text){
    if(!window.speechSynthesis || !text) return false;
    try{
      speechSynthesis.cancel();  // interrompe qualquer fala anterior
      const u = new SpeechSynthesisUtterance(text.replace(/^to /i, ''));
      u.lang = TARGET_LANG;
      u.rate = 0.78;  // devagar o suficiente pra separar as sílabas com clareza
      const v = pickVoice();
      if(v) u.voice = v;
      speechSynthesis.speak(u);
      return true;
    }catch(_){ return false; }
  }
  // Vozes carregam assíncronas em alguns navegadores
  if(window.speechSynthesis){
    speechSynthesis.addEventListener('voiceschanged', ()=>{ cachedVoice = null; pickVoice(); });
    pickVoice();
  }
  $('#tts-btn')?.addEventListener('click', ()=>{
    const en = $('#answer-en')?.textContent;
    if(en && en !== '—') speak(en);
  });
  // Esconde o botão TTS se o navegador não suportar
  if(!window.speechSynthesis) {
    const btn = $('#tts-btn');
    if(btn) btn.style.display = 'none';
  }

  // ============ Reconhecimento de fala (opt-in) ============
  // Web Speech API do navegador — zero servidor, zero armazenamento de
  // áudio. Chrome/Edge suportam bem; Firefox e Safari desktop têm suporte
  // irregular — nesses o botão nem aparece (feature detection).
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition = null;
  let recognizing = false;
  const voiceToggle = $('#voice-toggle');
  const voicePanel = $('#voice-panel');
  const inputEl = $('#nb-input');

  function applyVoiceMode(){
    // O modo (escrita/ditado/voz) foi escolhido antes da sessão. Aqui só
    // aplica o UI que corresponde. Sem toggle no meio da sessão — se quiser
    // trocar de modo, volta pro tópico e escolhe de novo (evita confusão
    // com prefs mistos entre modos).
    if(voiceToggle){ voiceToggle.hidden = true; }
    if(prefs.voice){
      if(voicePanel){ voicePanel.hidden = false; }
      if(inputEl){ inputEl.hidden = true; }
      const lab = $('#nb-label'); if(lab) lab.textContent = 'Fale a tradução em inglês';
    }else{
      if(voicePanel){ voicePanel.hidden = true; }
      if(inputEl){ inputEl.hidden = false; }
      const lab = $('#nb-label');
      if(lab){
        if(prefs.cue === 'ditado') lab.textContent = 'Escreva a tradução em português';
        else if(prefs.cue === 'transcricao') lab.textContent = 'Escreva em inglês o que você ouviu';
        else lab.textContent = 'Escreva a tradução em inglês';
      }
      if(recognition && recognizing){ try{ recognition.stop(); }catch(_){} }
    }
    updateConferirState();
  }
  // Roda uma vez no boot pra estado inicial da UI (label do notebook,
  // painel de voz visível/oculto conforme o modo escolhido).
  applyVoiceMode();

  // Grammar hints: JSGF list com todas as palavras em inglês do tópico —
  // o reconhecedor sabe QUAIS palavras esperar e prefere elas nas
  // alternativas. Isso aumenta MUITO a precisão pra sotaques (o servidor
  // do Google já usa essa dica pra pesar candidatos). Funciona em Chrome.
  const SpeechGrammarList = window.SpeechGrammarList || window.webkitSpeechGrammarList;
  let grammar = null;
  if(SpeechGrammarList && ALL_WORDS.length){
    const vocab = ALL_WORDS.map(w => (w.en || '').replace(/^to /i, '').trim())
      .filter(Boolean)
      .map(s => s.replace(/[^a-zA-Z0-9\s'-]/g, ''))
      .filter(Boolean);
    if(vocab.length){
      const rule = `#JSGF V1.0; grammar words; public <word> = ${vocab.join(' | ')} ;`;
      try{ grammar = new SpeechGrammarList(); grammar.addFromString(rule, 1); }catch(_){}
    }
  }

  // Contador de falhas consecutivas por palavra — depois de 2 tentativas
  // de voz sem match, oferecemos fallback pra digitação (o pior é ficar
  // preso na palavra).
  let voiceFailCount = 0;

  function startRecognition(){
    if(!SpeechRec) return;
    if(recognizing) return;
    if(!recognition){
      recognition = new SpeechRec();
      recognition.lang = TARGET_LANG;
      recognition.interimResults = false;
      // maxAlternatives 8 (era 3) — mais candidatos pra o matchAnswer
      // filtrar o certo. Custo praticamente zero.
      recognition.maxAlternatives = 8;
      if(grammar) recognition.grammars = grammar;
      recognition.onstart = ()=>{
        recognizing = true;
        $('#mic-btn')?.classList.add('rec');
        $('#voice-hint').textContent = 'ouvindo…';
      };
      recognition.onend = ()=>{
        recognizing = false;
        $('#mic-btn')?.classList.remove('rec');
      };
      recognition.onerror = (ev)=>{
        recognizing = false;
        $('#mic-btn')?.classList.remove('rec');
        const msg = ev.error === 'not-allowed'
          ? 'permissão de microfone negada — clique no cadeado da barra e libere'
          : ev.error === 'no-speech'
            ? 'não ouvi nada — tente de novo'
            : ev.error === 'audio-capture'
              ? 'não achei o microfone'
              : 'não deu — tente de novo';
        $('#voice-hint').textContent = msg;
        voiceFailCount++;
        maybeOfferKeyboardFallback();
      };
      recognition.onresult = (ev)=>{
        // Voz reformulada como SHADOWING (não mais juiz binário).
        //
        // Por quê: SpeechRecognition calibrado pra fala nativa produz
        // sistematicamente falsos negativos (aluno falou certo, ASR
        // rejeitou → frustração, filtro afetivo alto, abandono da fala)
        // E falsos positivos (aluno falou errado, ASR aceitou →
        // consolidação do erro, caminho pra fossilização). Nas duas
        // pontas o feedback binário do ASR era veneno pedagógico.
        //
        // Agora: o ASR vira CONSELHEIRO tolerante. Mostra o que ouviu +
        // uma sugestão suave ("soou compreensível" / "consegui distinguir
        // o final"). A REVELAÇÃO fica com o próprio aluno: ele ouve a
        // palavra tocada pelo TTS, se auto-avalia com 3 botões
        // (Errei/Quase/Sabia) e o app confia. Isso alinha com literatura
        // de shadowing (Krashen sobre affective filter; Long sobre
        // interação com feedback recastly).
        const w = currentWord();
        const alts = [];
        for(let i=0;i<ev.results[0].length;i++){
          alts.push(ev.results[0][i].transcript || '');
        }
        let best = alts[0];
        let matchLevel = 'off';  // 'ok' | 'close' | 'off'
        for(const alt of alts){
          const m = matchAnswer(alt, w.en);
          if(m === 'ok'){ best = alt; matchLevel = 'ok'; break; }
          if(m === 'close' && matchLevel !== 'close'){ best = alt; matchLevel = 'close'; }
        }
        // Reset o counter — se OU ok OU close, achamos algo relacionado
        if(matchLevel !== 'off') voiceFailCount = 0;
        else voiceFailCount++;
        // Feedback do ASR como sinal SUAVE. Nunca decide o resultado.
        const asrHint = matchLevel === 'ok'
          ? '<span class="asr-ok">✓ soou compreensível</span>'
          : matchLevel === 'close'
            ? '<span class="asr-close">≈ próximo do alvo</span>'
            : '<span class="asr-off">o reconhecedor ouviu algo diferente — pode ser o sotaque, tenta de novo se quiser</span>';
        const alternatives = alts.slice(1, 3).filter(a => a && a !== best);
        const altText = alternatives.length
          ? `<span class="voice-alts">também ouvi: ${alternatives.map(a=>`"${a}"`).join(', ')}</span>`
          : '';
        $('#voice-heard').innerHTML = `<div class="voice-heard-main">"${best}"</div>${asrHint}${altText ? '<br>' + altText : ''}`;
        // Toca a resposta modelo pra shadowing (ouvir a diferença)
        setTimeout(()=>speak(w.en), 200);
        // Revela a resposta + 3 botões de auto-avaliação
        setTimeout(()=>showVoiceSelfAssess(w, best), 500);
        maybeOfferKeyboardFallback();
      };
    }
    try{
      recognition.lang = TARGET_LANG;
      $('#voice-heard').textContent = '';
      recognition.start();
    }catch(_){
      // já rodando — ignora
    }
  }

  // Shadowing self-assessment — aluno ouve a palavra modelo e se
  // auto-avalia com 3 botões. Bypassa completamente o julgamento
  // binário do ASR. Alinha com Krashen (affective filter baixo) e
  // com skill acquisition theory (auto-monitoramento).
  function showVoiceSelfAssess(w, spoken){
    st.revealed = true;
    $('#answer').classList.add('on');
    $('#answer-en').textContent = w.en;
    $('#answer-pt').textContent = w.pt;
    const wrap = $('#controls');
    wrap.className = 'controls voice-assess';
    wrap.innerHTML = `
      <div class="assess-label">Como foi sua pronúncia?</div>
      <div class="assess-buttons">
        <button class="btn miss" id="va-miss">Errei</button>
        <button class="btn gold" id="va-close">Quase</button>
        <button class="btn primary" id="va-know">Sabia</button>
      </div>
    `;
    const applyResult = (result) => {
      const el = $('#verdict');
      if(el){
        const msgs = {miss:'✗ Volta amanhã.', close:'≈ Repete pra fixar.', know:'✓ Segue jogo.'};
        el.innerHTML = msgs[result];
        el.className = 'verdict ' + (result==='know'?'ok':result==='close'?'close':'no');
      }
      if(result==='miss' && !st.sessionMissed.includes(w.id)) st.sessionMissed.push(w.id);
      st.sessionAnswers.push({wordId:w.id, pt:w.pt, en:w.en, answer:spoken, result});
      syncWord(w.id, result, result==='miss' ? spoken : '');
      wrap.className = 'controls single';
      wrap.innerHTML = `<button class="btn primary" id="next-btn">Continuar <kbd>Enter</kbd></button>`;
      $('#next-btn').addEventListener('click', next);
    };
    $('#va-miss')?.addEventListener('click', ()=>applyResult('miss'));
    $('#va-close')?.addEventListener('click', ()=>applyResult('close'));
    $('#va-know')?.addEventListener('click', ()=>applyResult('know'));
  }

  function maybeOfferKeyboardFallback(){
    // 2 falhas seguidas: oferece caminho digitado. Nao força, oferece.
    if(voiceFailCount < 2) return;
    const hintEl = $('#voice-hint');
    if(!hintEl) return;
    if(hintEl.querySelector('.fallback-btn')) return;  // já oferecido
    hintEl.innerHTML = `Não estou reconhecendo bem. <button type="button" class="fallback-btn" id="fb-typed">Digitar em vez de falar nesta palavra</button>`;
    $('#fb-typed')?.addEventListener('click', ()=>{
      $('#voice-panel').hidden = true;
      inputEl.hidden = false;
      inputEl.focus({preventScroll:true});
      voiceFailCount = 0;
    });
  }
  $('#mic-btn')?.addEventListener('click', startRecognition);

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
      // Alvo da resposta muda por modo:
      //   - ditado: aluno ouviu inglês e escreve tradução em português
      //   - transcricao / PT / Foto / Voz: alvo é o inglês (w.en)
      const target = prefs.cue === 'ditado' ? w.pt : w.en;
      const v = matchAnswer(typed, target);
      // Diff tipográfico: mostra o que foi digitado com as letras certas
      // em tinta e as diferentes em vermelho — feedback é o próprio texto,
      // não precisa de ícone. Uma vozinha de professor sem palavra escrita.
      const diffHTML = buildDiff(typed, target);
      if(v==='ok'){
        el.innerHTML = '<span class="verdict-mark ok">✓</span> Perfeito.';
        el.className='verdict ok';
        result='know';
      } else if(v==='close'){
        el.innerHTML = `<span class="verdict-mark close">≈</span> Quase — veja a grafia. <span class="diff">${diffHTML}</span>`;
        el.className='verdict close';
        result='soso';
      } else {
        el.innerHTML = `<span class="verdict-mark no">✗</span> Não bateu. <span class="diff">${diffHTML}</span>`;
        el.className='verdict no';
        result='miss';
      }
    }
    if(result==='miss' && !st.sessionMissed.includes(w.id)) st.sessionMissed.push(w.id);
    // "answer" é o texto que a pessoa produziu — pode ser digitado ou
    // reconhecido por voz. O coach usa junto com STUDY_MODE pra saber
    // o verbo certo ("falou" vs "escreveu").
    st.sessionAnswers.push({wordId:w.id, pt:w.pt, en:w.en, answer:typed, result});
    syncWord(w.id, result, result==='miss' ? typed : '');
    // Auto-play da pronúncia quando revela — reforça a memória auditiva.
    // Só toca se veio de miss/soso/close (aprendizado). Em 'know' também
    // toca de leve, ajuda a fixar. Usuário pode clicar de novo pra repetir.
    speak(w.en);
    renderControls();
  }
  function syncWord(wordId, result, wrongAnswer){
    // Modo desafio: manda o mode pro backend, que não altera o SRS.
    // Ainda registramos pra o coach de sessão poder comentar a rodada.
    const modeParam = window.CHALLENGE_MODE ? '&mode=challenge' : '';
    // Idioma da resposta — Ditado responde em português, resto em inglês.
    // Guardado com o last_wrong pra "última vez você escreveu X" só
    // aparecer no mesmo modo depois.
    const answerLang = prefs.cue === 'ditado' ? 'pt' : 'en';
    return fetch(`${window.MARK_URL_BASE}${wordId}/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': window.CSRF_TOKEN, 'Content-Type': 'application/x-www-form-urlencoded' },
      body: `result=${result}&wrong_answer=${encodeURIComponent(wrongAnswer||'')}&answer_lang=${answerLang}${modeParam}`,
    }).catch(()=>{});
  }
  function next(){ st.i++; st.revealed = false; renderCard(); }

  function renderDone(){
    const missedCount = st.sessionMissed.length;
    const total = WORDS.length;
    const rightCount = total - missedCount;
    const pct = total ? Math.round(rightCount / total * 100) : 0;
    // Feedback LOCAL — aparece instantaneamente antes da IA responder.
    // Antes a pessoa via só "pensando…" por 5-10s sem sinal nenhum.
    const missedList = st.sessionAnswers
      .filter(a => a.result === 'miss')
      .slice(0, 5)
      .map(a => `<span class="missed-word">${escapeHtml(a.pt)} <em>→</em> ${escapeHtml(a.en)}</span>`)
      .join('');
    const localSummary = missedCount
      ? `<div class="local-summary"><div class="ls-label">Erradas nessa rodada</div><div class="ls-words">${missedList}</div></div>`
      : `<div class="local-summary ok"><div class="ls-label">Zero erros</div></div>`;
    const wrap = $('#card');
    wrap.innerHTML = `
      <div class="round-done">
        <div class="done-label">Rodada completa</div>
        <div class="done-score"><b>${rightCount}</b> <span class="done-slash">/</span> ${total} <span class="done-pct">${pct}%</span></div>
        <p class="done-sub">${missedCount ? `${missedCount} ${missedCount===1?'palavra pra revisar':'palavras pra revisar'} agora.` : 'Perfeito. Volte amanhã pra próxima rodada.'}</p>
        ${localSummary}
        <div class="coach-slot" id="coach-slot" hidden>
          <div class="coach-label">Coach</div>
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
        st.sessionMissed = []; st.sessionAnswers = []; st.i = 0; st.revealed = false;
        // restaura o card e o input antes de renderizar a próxima rodada
        $('#card').innerHTML = ORIGINAL_CARD_HTML;
        $('#notebook').style.display = '';
        // re-liga o listener de input (o elemento foi substituído)
        $('#nb-input')?.addEventListener('input', updateConferirState);
        $('#nb-input')?.addEventListener('keydown', onInputKeydown);
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
    // Skeleton — barras animadas em vez de "pensando…" texto morto. Dá
    // sinal visual de que algo tá acontecendo sem prometer conteúdo.
    $('#coach-msg').innerHTML = '<span class="coach-skeleton"><span></span><span></span><span></span></span>';
    try{
      const res = await fetch(window.COACH_URL, {
        method: 'POST',
        headers: {'X-CSRFToken': window.CSRF_TOKEN, 'Content-Type': 'application/json'},
        body: JSON.stringify({topic: window.TOPIC_NAME, mode: STUDY_MODE, answers: st.sessionAnswers}),
      });
      const json = await res.json();
      if(!json.enabled || !json.message){
        // Sem chave configurada, ou IA respondeu vazio/erro — melhor
        // sumir com o painel do que mostrar "sem comentário".
        slot.hidden = true;
        return;
      }
      $('#coach-msg').textContent = json.message;
    }catch(_){
      slot.hidden = true;
    }
  }

  function initModebar(){
    // Só existe no modo Escrita e só quando o tópico tem fotos. Alterna
    // entre ver a palavra em português (cue='pt') e ver uma foto do
    // conceito (cue='foto') dentro do MESMO modo.
    $$('.modebar button').forEach(b=>{
      b.classList.toggle('on', b.dataset.cue===prefs.cue);
      b.addEventListener('click', (e)=>{
        e.preventDefault();
        b.blur();
        if(prefs.cue === b.dataset.cue) return;
        $$('.modebar button').forEach(x=>x.classList.remove('on'));
        b.classList.add('on');
        prefs.cue = b.dataset.cue;
        savePrefs();
        renderCard();
      });
    });
  }

  function onInputKeydown(e){
    if(e.key==='Enter'){
      if(st.revealed){ next(); return; }
      const typed = e.target.value.trim();
      if(typed) reveal();
      // Enter vazio: nada acontece (protege recall ativo)
    }
  }
  $('#nb-input')?.addEventListener('input', updateConferirState);
  $('#nb-input')?.addEventListener('keydown', onInputKeydown);
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
