"""
Busca a foto de uma palavra em inglês pra mostrar no modo "Foto".

Fluxo:
1. Constrói query melhorada (adiciona contexto quando o termo é ambíguo).
2. Puxa vários candidatos do Pexels.
3. Ranqueia por alt text (a palavra aparece? é o assunto principal?).
4. Rejeita candidatos ruins (assunto errado, cena genérica).
5. Se nada passa no threshold, tenta Wikipedia como fallback.
6. Se ainda nada, devolve found=False → app mostra o texto sem foto.

Escolha: alt text ranking > download-e-classifica-pixels. Muito mais
barato, sem custo de API extra, e o alt do Pexels é escrito por humanos
(alta qualidade). Pra casos duros existe validate_with_vision() usando
Gemini multimodal, mas é opcional (custa quota).
"""
import os

import httpx

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
PEXELS_ENABLED = bool(PEXELS_API_KEY)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

WIKI_HEADERS = {
    "User-Agent": "CadernoDeIdiomas/1.0 (app pessoal de flashcards; contato: brzueira342386@gmail.com)"
}


# --- Regras de query --------------------------------------------------------
# Termos ambíguos ou genéricos ganham contexto pra puxar imagens melhores.
# Ex: "family" sozinho traz árvore genealógica, logo, retrato — mistura.
# "family portrait" foca em fotos de família de verdade.
QUERY_OVERRIDES = {
    # animais que confundem com outros
    "seal": "seal animal",
    "bear": "bear animal",
    "bull": "bull animal",
    "swan": "swan bird",
    "crane": "crane bird",
    "hawk": "hawk bird",
    "mouse": "mouse rodent",
    "rat": "rat rodent",
    # comidas que só aparecem em pratos
    "lettuce": "lettuce leaf head",
    "spinach": "spinach leaves",
    "cilantro": "cilantro fresh herb",
    "parsley": "parsley fresh herb",
    "basil": "basil fresh leaves",
    "mint": "mint leaves",
    "arugula": "arugula leaves",
    "kale": "kale leaves",
    "cabbage": "cabbage whole head",
    "onion": "raw onion",
    "garlic": "garlic bulb clove",
    "flour": "flour baking ingredient",
    "sugar": "sugar bowl white",
    "salt": "salt crystals bowl",
    # abstrações que precisam de composição
    "family": "family portrait together",
    "friend": "two friends together portrait",
    "friends": "friends group happy",
    "friendship": "friends laughing together",
    "love": "couple in love",
    "happiness": "happy smiling portrait",
    "birthday": "birthday cake candles party",
    "wedding": "wedding ceremony bride groom",
    # profissões devem mostrar a pessoa fazendo o trabalho
    "doctor": "doctor stethoscope hospital",
    "teacher": "teacher classroom",
    "nurse": "nurse hospital scrubs",
    "chef": "chef kitchen cooking",
    "waiter": "waiter restaurant serving",
    "firefighter": "firefighter uniform action",
    "police officer": "police officer uniform",
    "carpenter": "carpenter working wood",
    "electrician": "electrician working wiring",
    "plumber": "plumber pipes tools",
    "farmer": "farmer field working",
    "baker": "baker bread bakery",
    "gardener": "gardener plants working",
    "mechanic": "mechanic car repair",
    "photographer": "photographer camera portrait",
    "dentist": "dentist office chair",
    "veterinarian": "veterinarian animal clinic",
    "architect": "architect blueprint drawing",
    "designer": "designer working computer",
    # corpo — sempre pegar close/anatomia
    "head": "human head portrait",
    "hair": "human hair closeup",
    "eye": "human eye closeup",
    "nose": "human nose closeup",
    "mouth": "human mouth closeup",
    "hand": "human hand closeup",
    "foot": "human foot",
    "heart": "heart anatomy",
    "brain": "brain anatomy",
    # partes do carro
    "tire": "car tire wheel",
    "engine": "car engine mechanic",
    "steering wheel": "car steering wheel driver",
    # coisas de casa que se confundem
    "bed": "bed bedroom furniture",
    "chair": "chair furniture",
    "table": "table furniture wood",
    "sofa": "sofa couch living room",
}

# Palavras cujo alt text costuma indicar que a foto é ruim pro nosso caso
# (aparecem em cenas onde o assunto solicitado é secundário).
BAD_CONTEXT_TERMS = {
    "salad", "sandwich", "burger", "pizza", "buffet", "restaurant",
    "market", "grocery", "supermarket", "kitchen counter",
    "wedding table", "party table", "collection",
    "assortment", "variety",
}

# Termos vagamente relacionados que atrapalham pra animais/objetos
# específicos (ex: pegar foto de "vitrine" pra "tomate").
GENERIC_SCENES = {
    "store display", "store shelf", "market stall",
}

# Pexels tem muita foto "editorial" — bonita pra ilustração de blog, péssima
# pra flashcard didático (o objeto vira pretexto pra composição artística
# em vez de ser mostrado com clareza). Esses termos no alt são sinal forte
# de que a foto não vai servir pra ensinar a palavra.
ARTSY_NEGATIVE_TERMS = {
    "abstract", "artistic", "moody", "dimly", "vintage", "rustic",
    "silhouette", "monochrome", "sketch", "drawing", "illustration",
    "painted", "graffiti", "reflection", "reflecting", "shadow", "shadows",
    "frozen", "spiral", "surreal", "blur", "blurred", "bokeh", "dramatic",
    "conceptual", "minimalist", "aesthetic", "textured wall", "grunge",
    "faded", "sepia", "double exposure", "calligraphy", "still life",
    "eerie", "abandoned", "unrecognizable", "misted", "editorial",
}

# Palavras que, aparecendo como o SUJEITO da foto (logo no início do alt),
# indicam que uma pessoa é o assunto principal — não o objeto que estamos
# procurando. Uma foto de "mulher usando chapéu" não ensina "chapéu" tão
# bem quanto uma foto do chapéu isolado. Exceção: PERSON_SUBJECT_TERMS
# abaixo, onde a pessoa É o ponto (profissões, família, emoções).
PERSON_LEAD_WORDS = {
    "woman", "man", "person", "girl", "boy", "model", "lady", "guy",
    "kid", "child", "children", "people", "couple", "friends", "portrait",
}

# Termos cujo conceito EXIGE uma pessoa na foto — aqui o PERSON_LEAD_WORDS
# não deve penalizar.
PERSON_SUBJECT_TERMS = {
    "doctor", "teacher", "nurse", "chef", "waiter", "firefighter",
    "police officer", "carpenter", "electrician", "plumber", "farmer",
    "baker", "gardener", "mechanic", "photographer", "dentist",
    "veterinarian", "architect", "designer", "family", "friend", "friends",
    "friendship", "love", "wedding", "mother", "father", "son", "daughter",
    "brother", "sister", "grandmother", "grandfather", "baby", "child",
    "man", "woman", "boy", "girl", "person",
}


PEXELS_PER_PAGE = 15  # mais candidatos = mais chances de achar uma boa


def _score_candidate(alt: str, en_word: str) -> int:
    """Score 0-100. >0 = candidato válido, <=0 = rejeitar.

    Regras:
    - alt vazio = 20 (aceita mas sem confiança)
    - palavra aparece no alt = +40
    - palavra aparece como PRIMEIRA palavra do alt = +20 (é o assunto)
    - alt curto (<= 7 palavras) e contém = +15 (foto específica)
    - alt muito longo (>= 15 palavras) = -10 (cena complexa, provavelmente errado)
    - contém termo de contexto ruim = -30
    - contém cena genérica = -20
    """
    alt_lower = (alt or "").lower().strip()
    en_clean = en_word.lower().replace("to ", "").strip()
    # extrai palavra-chave: pra "police officer" usa "police officer",
    # pra "steering wheel" idem. Mas também tenta a última palavra sozinha.
    key_terms = [en_clean]
    if " " in en_clean:
        key_terms.append(en_clean.split()[-1])  # última palavra ("wheel" p/ "steering wheel")

    if not alt_lower:
        return 20  # sem alt: neutro, pode ser boa foto sem legenda

    words = alt_lower.split()
    score = 0

    # 1. Palavra aparece? Onde?
    hit = False
    position = -1
    for term in key_terms:
        idx = alt_lower.find(term)
        if idx == -1:
            continue
        # Conta a posição da palavra dentro do array de palavras.
        # Palavra que aparece no início = provavelmente o assunto.
        # Palavra que aparece no meio/fim = provavelmente um detalhe.
        try:
            position = next(i for i, w in enumerate(words)
                            if w == term or w.startswith(term + "s") or w.rstrip(",.").rstrip("s") == term)
        except StopIteration:
            position = 999
        score += 40
        hit = True
        if position == 0:
            score += 25  # primeira palavra = definitivamente o assunto
        elif position <= 2:
            score += 15  # top 3 = provavelmente o assunto
        elif position <= 5:
            score += 5   # aparece cedo, ok
        elif position >= 10:
            score -= 15  # aparece só no final = detalhe, não assunto
        break
    if not hit:
        return -50

    # 2. Especificidade (alt curto = foto focada)
    if len(words) <= 7:
        score += 15
    elif len(words) >= 18:
        score -= 15

    # 3. Termos ruins de contexto (assunto conflitante)
    for bad in BAD_CONTEXT_TERMS:
        if bad in alt_lower and bad != en_clean:
            score -= 30
    for bad in GENERIC_SCENES:
        if bad in alt_lower:
            score -= 20

    # 4. Fotografia "editorial/artística" — objeto vira pretexto pra
    # composição bonita em vez de ser mostrado com clareza didática.
    artsy_hits = sum(1 for term in ARTSY_NEGATIVE_TERMS if term in alt_lower)
    if artsy_hits:
        score -= min(artsy_hits * 22, 66)

    # 5. Pessoa é o sujeito da foto, não o objeto pedido — a não ser que o
    # próprio conceito exija uma pessoa (profissão, família, emoção).
    # Checa se alguma palavra-de-pessoa aparece ANTES do termo buscado —
    # não só como primeira palavra (evita falso-negativo tipo "Elegant
    # woman in hat...", onde "elegant" precede "woman").
    if en_clean not in PERSON_SUBJECT_TERMS and position not in (-1, 999):
        clean_words = [w.rstrip(",.") for w in words]
        person_idx = next((i for i, w in enumerate(clean_words) if w in PERSON_LEAD_WORDS), None)
        if person_idx is not None and person_idx < position:
            score -= 25

    return score


def _pexels_search(query: str) -> list[dict]:
    """Só a chamada bruta ao Pexels. Retorna lista de photos ou []."""
    try:
        resp = httpx.get(
            "https://api.pexels.com/v1/search",
            params={"query": query, "per_page": PEXELS_PER_PAGE, "orientation": "square"},
            headers={"Authorization": PEXELS_API_KEY},
            timeout=8,
        )
    except httpx.HTTPError:
        return []
    if resp.status_code != 200:
        return []
    return resp.json().get("photos") or []


# Piso de aceitação. Score positivo mas baixo (ex: 15) normalmente
# significa "a palavra aparece, mas a foto é fraca" (pessoa como sujeito,
# posição ambígua, nada de bônus de especificidade) — melhor cair pro
# fallback do que mostrar uma foto que não ensina nada.
MIN_ACCEPT_SCORE = 20


def _rank_photos(photos: list[dict], q_original: str) -> list[dict]:
    """Ranqueia e filtra os candidatos crus."""
    scored = []
    for p in photos:
        alt = p.get("alt", "")
        src = p.get("src", {})
        url = src.get("large") or src.get("medium") or src.get("original")
        if not url:
            continue
        score = _score_candidate(alt, q_original)
        if score < MIN_ACCEPT_SCORE:
            continue
        scored.append({
            "score": score,
            "url": url,
            "page": p.get("url", ""),
            "credit": p.get("photographer", ""),
            "alt": alt,
        })
    scored.sort(key=lambda x: -x["score"])
    return scored


def _fetch_pexels(q_original: str) -> dict | None:
    if not PEXELS_API_KEY:
        return None
    q_lower = q_original.lower()
    q_used = QUERY_OVERRIDES.get(q_lower, q_original)

    # Tenta com a query melhorada (ou original se não há override)
    photos = _pexels_search(q_used)
    scored = _rank_photos(photos, q_original)

    # Fallback 1: se usou override e nada passou, tenta o termo original
    if not scored and q_used != q_original:
        photos = _pexels_search(q_original)
        scored = _rank_photos(photos, q_original)

    if not scored:
        return None

    variants = [{"url": s["url"], "page": s["page"], "credit": s["credit"]} for s in scored[:8]]
    best = scored[0]
    return {
        "found": True,
        "url": best["url"],
        "page": best["page"],
        "title": q_original,
        "credit": best["credit"],
        "source": "pexels",
        "variants": variants,
        "top_score": best["score"],
        "top_alt": best["alt"],
    }


def _fetch_wikipedia(q: str) -> dict | None:
    title = q.strip().replace(" ", "_")
    if not title:
        return None
    try:
        resp = httpx.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}",
            headers=WIKI_HEADERS, timeout=8, follow_redirects=True,
        )
    except httpx.HTTPError:
        return None
    if resp.status_code != 200:
        return None
    data = resp.json()
    thumb = data.get("thumbnail")
    if thumb and data.get("type") != "disambiguation":
        page = data.get("content_urls", {}).get("desktop", {}).get("page", "")
        variants = [{"url": thumb["source"], "page": page, "credit": "Wikipedia"}]
        return {
            "found": True,
            "url": thumb["source"],
            "page": page,
            "title": data.get("title", q),
            "credit": "Wikipedia",
            "source": "wikipedia",
            "variants": variants,
        }
    return None


def fetch_photo(q: str) -> dict:
    """{'found': False} ou {'found': True, 'url', 'page', 'title', 'credit', 'source', 'variants', ...}"""
    q = q.strip()
    if not q:
        return {"found": False}
    return _fetch_pexels(q) or _fetch_wikipedia(q) or {"found": False}


# ---------- Validação opcional com Gemini Vision ----------
# Uso: durante check_photos --strict, chama isso pra verificar se a foto
# realmente mostra o objeto. Custa quota de Gemini, então é opt-in.

def validate_with_vision(image_url: str, en_word: str) -> dict | None:
    """Pergunta ao Gemini se a imagem realmente mostra a palavra como
    assunto principal. Retorna {"ok": bool, "score": 0-10, "reason": "..."}
    ou None se a API falhar."""
    if not GEMINI_API_KEY:
        return None
    prompt = (
        f'Look at this image. Is "{en_word}" clearly the MAIN SUBJECT? '
        'Return ONLY JSON: {"ok": true|false, "score": 0-10, "reason": "one short sentence"}. '
        'Rules:\n'
        f'- ok=true only if "{en_word}" is unambiguously the main focus of the photo.\n'
        f'- ok=false if the photo shows something else with "{en_word}" only in background/secondary.\n'
        f'- ok=false if the photo shows a category/collection/scene rather than the object itself.\n'
        '- score 0-10: 10 = perfect standalone photo, 5 = present but not focal, 0 = not shown or wrong subject.\n'
    )
    try:
        # Fetch image and inline as base64
        img_resp = httpx.get(image_url, timeout=10, follow_redirects=True)
        if img_resp.status_code != 200:
            return None
        import base64
        img_b64 = base64.b64encode(img_resp.content).decode("ascii")
        mime = img_resp.headers.get("content-type", "image/jpeg").split(";")[0]

        resp = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={GEMINI_API_KEY}",
            json={
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": mime, "data": img_b64}},
                    ]
                }]
            },
            timeout=25,
        )
        if resp.status_code != 200:
            return None
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        # extrai JSON balanceado
        import json
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return None
        data = json.loads(text[start:end + 1])
        return {
            "ok": bool(data.get("ok")),
            "score": int(data.get("score", 0)),
            "reason": str(data.get("reason", "")),
        }
    except (httpx.HTTPError, KeyError, ValueError, IndexError):
        return None
