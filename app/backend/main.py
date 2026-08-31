"""
Backend do Caderno de Idiomas.

Responsabilidades hoje:
- servir a lista de topicos/palavras (data/words.json)
- fazer proxy de busca de fotos na Wikimedia Commons (esconde a chamada
  externa do front, permite cache e trocar de provedor de imagem sem
  mexer no cliente)

Responsabilidades futuras (ver README):
- autenticacao de usuario via Supabase Auth (o front pede o login pro
  Supabase direto e manda o token aqui; este backend so valida o token)
- salvar progresso (palavras "sabidas") por usuario no Postgres do Supabase
- logica de assinatura/paywall, se decidir vender
"""
import json
import os
import time
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "words.json"

app = FastAPI(title="Caderno de Idiomas API")

# Em producao, troque "*" pela URL real do front (ex: https://seuapp.vercel.app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_words_cache: Optional[dict] = None


def load_words() -> dict:
    global _words_cache
    if _words_cache is None:
        with open(DATA_PATH, encoding="utf-8") as f:
            _words_cache = json.load(f)
    return _words_cache


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/topics")
def get_topics():
    """Lista todos os topicos com suas palavras."""
    return load_words()


@app.get("/api/topics/{topic_id}")
def get_topic(topic_id: str):
    data = load_words()
    topic = next((t for t in data["topics"] if t["id"] == topic_id), None)
    if not topic:
        raise HTTPException(status_code=404, detail="Topico nao encontrado")
    return topic


# --- Proxy de imagens (Wikimedia Commons, sem chave) -----------------------

_image_cache: dict[str, tuple[float, Optional[dict]]] = {}
IMAGE_CACHE_TTL = 60 * 60 * 24  # 1 dia


@app.get("/api/image")
async def get_image(q: str):
    """Busca uma foto real na Wikimedia Commons para a palavra `q`."""
    now = time.time()
    cached = _image_cache.get(q.lower())
    if cached and now - cached[0] < IMAGE_CACHE_TTL:
        return cached[1] or {"found": False}

    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": f"{q} filetype:bitmap",
        "gsrlimit": 6,
        "gsrnamespace": 6,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": 480,
        "format": "json",
    }
    headers = {"User-Agent": "CadernoDeIdiomas/1.0 (app pessoal de flashcards; contato: brzueira342386@gmail.com)"}
    async with httpx.AsyncClient(timeout=8, headers=headers) as client:
        resp = await client.get("https://commons.wikimedia.org/w/api.php", params=params)
        resp.raise_for_status()
        payload = resp.json()

    pages = (payload.get("query") or {}).get("pages") or {}
    candidates = [p for p in pages.values() if p.get("imageinfo")]
    if not candidates:
        _image_cache[q.lower()] = (now, None)
        return {"found": False}

    info = candidates[0]["imageinfo"][0]
    title = candidates[0].get("title", "").removeprefix("File:")
    title = title.rsplit(".", 1)[0]
    result = {
        "found": True,
        "url": info.get("thumburl") or info.get("url"),
        "page": info.get("descriptionurl"),
        "title": title,
    }
    _image_cache[q.lower()] = (now, result)
    return result


# --- Progresso do usuario (Supabase Auth + Postgres) ------------------------
#
# Para ativar: crie um projeto gratis em supabase.com, rode o schema em
# supabase/schema.sql, e defina SUPABASE_URL + SUPABASE_KEY no .env
# (copie de .env.example). O front usa o Supabase JS SDK para login e manda
# o access_token no header Authorization aqui. Enquanto nao configurado,
# estes endpoints respondem 503 com uma mensagem clara em vez de derrubar
# o servidor.

_supabase_client = None
_supabase_configured = bool(os.getenv("SUPABASE_URL")) and bool(os.getenv("SUPABASE_KEY"))


def get_supabase():
    global _supabase_client
    if not _supabase_configured:
        raise HTTPException(
            status_code=503,
            detail="Login ainda nao configurado neste servidor (falta SUPABASE_URL/SUPABASE_KEY no .env)",
        )
    if _supabase_client is None:
        from supabase import create_client
        _supabase_client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    return _supabase_client


def current_user_id(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Faca login para usar essa funcao")
    token = authorization.removeprefix("Bearer ").strip()
    supabase = get_supabase()
    user = supabase.auth.get_user(token)
    if not user or not user.user:
        raise HTTPException(status_code=401, detail="Sessao invalida ou expirada")
    return user.user.id


@app.get("/api/progress")
def get_progress(authorization: str = Header(None)):
    """Retorna todas as palavras marcadas como sabidas pelo usuario logado."""
    user_id = current_user_id(authorization)
    supabase = get_supabase()
    res = supabase.table("progress").select("topic_id,word_index").eq("user_id", user_id).execute()
    return {"items": res.data}


class ProgressItem(BaseModel):
    topic_id: str
    word_index: int


class ProgressBulk(BaseModel):
    items: list[ProgressItem]


@app.post("/api/progress/bulk")
def bulk_progress(body: ProgressBulk, authorization: str = Header(None)):
    """Envia de uma vez todas as palavras sabidas localmente (usado ao logar)."""
    user_id = current_user_id(authorization)
    if not body.items:
        return {"ok": True, "synced": 0}
    supabase = get_supabase()
    rows = [{"user_id": user_id, "topic_id": i.topic_id, "word_index": i.word_index} for i in body.items]
    supabase.table("progress").upsert(rows).execute()
    return {"ok": True, "synced": len(rows)}


@app.post("/api/progress/{topic_id}/{word_index}")
def mark_known(topic_id: str, word_index: int, known: bool, authorization: str = Header(None)):
    user_id = current_user_id(authorization)
    supabase = get_supabase()
    if known:
        supabase.table("progress").upsert({
            "user_id": user_id, "topic_id": topic_id, "word_index": word_index,
        }).execute()
    else:
        supabase.table("progress").delete().eq("user_id", user_id) \
            .eq("topic_id", topic_id).eq("word_index", word_index).execute()
    return {"ok": True}
