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


def _fetch_pexels(q: str) -> dict | None:
    if not PEXELS_API_KEY:
        return None
    try:
        resp = httpx.get(
            "https://api.pexels.com/v1/search",
            params={"query": q, "per_page": 1, "orientation": "square"},
            headers={"Authorization": PEXELS_API_KEY},
            timeout=8,
        )
    except httpx.HTTPError:
        return None
    if resp.status_code != 200:
        return None
    photos = resp.json().get("photos") or []
    if not photos:
        return None
    photo = photos[0]
    src = photo.get("src", {})
    url = src.get("large") or src.get("medium") or src.get("original")
    if not url:
        return None
    return {
        "found": True,
        "url": url,
        "page": photo.get("url", ""),
        "title": q,
        "credit": photo.get("photographer", ""),
        "source": "pexels",
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
        return {
            "found": True,
            "url": thumb["source"],
            "page": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
            "title": data.get("title", q),
            "credit": "Wikipedia",
            "source": "wikipedia",
        }
    return None


def fetch_photo(q: str) -> dict:
    """{'found': False} ou {'found': True, 'url', 'page', 'title', 'credit', 'source'}"""
    q = q.strip()
    if not q:
        return {"found": False}
    return _fetch_pexels(q) or _fetch_wikipedia(q) or {"found": False}
