"""
Busca a foto de uma palavra em inglês pra mostrar no modo "Foto".

Ordem: Pexels primeiro (busca de fotos de verdade — muito mais literal pro
objeto/animal/pessoa pedido) e Wikipedia como fallback só quando o Pexels
não tem resultado ou a chave não está configurada (sem chave, o app
continua funcionando, só usa direto o fallback).
"""
import os

import httpx

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
PEXELS_ENABLED = bool(PEXELS_API_KEY)

WIKI_HEADERS = {
    "User-Agent": "CadernoDeIdiomas/1.0 (app pessoal de flashcards; contato: brzueira342386@gmail.com)"
}


PEXELS_PER_PAGE = 8  # buscamos várias pra depois sortear uma no cliente


def _fetch_pexels(q: str) -> dict | None:
    if not PEXELS_API_KEY:
        return None
    try:
        resp = httpx.get(
            "https://api.pexels.com/v1/search",
            params={"query": q, "per_page": PEXELS_PER_PAGE, "orientation": "square"},
            headers={"Authorization": PEXELS_API_KEY},
            timeout=8,
        )
    except httpx.HTTPError:
        return None
    if resp.status_code != 200:
        return None
    photos = resp.json().get("photos") or []
    variants = []
    for p in photos:
        src = p.get("src", {})
        u = src.get("large") or src.get("medium") or src.get("original")
        if not u:
            continue
        variants.append({
            "url": u,
            "page": p.get("url", ""),
            "credit": p.get("photographer", ""),
        })
    if not variants:
        return None
    first = variants[0]
    return {
        "found": True,
        # url/page/credit continuam sendo a "capa" (pra compat com quem só
        # lê o campo scalar), mas variants tem TODAS pra rotação no cliente.
        "url": first["url"],
        "page": first["page"],
        "title": q,
        "credit": first["credit"],
        "source": "pexels",
        "variants": variants,
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
    # "disambiguation" = página de lista de sentidos, não uma imagem
    # específica da palavra — melhor não mostrar nada do que mostrar errado.
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
    """{'found': False} ou {'found': True, 'url', 'page', 'title', 'credit', 'source'}"""
    q = q.strip()
    if not q:
        return {"found": False}
    return _fetch_pexels(q) or _fetch_wikipedia(q) or {"found": False}
