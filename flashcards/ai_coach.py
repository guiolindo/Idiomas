"""
Coach com IA: de tempos em tempos (no máximo 1x por hora de atividade —
ver `should_generate_feedback` em views.py), manda um resumo do progresso
recente do aluno pra uma IA e guarda de volta uma mensagem curta e
específica sobre o que ele deve focar a seguir.

Gemini é tentado primeiro, Groq é o fallback (outro provedor, outra
infraestrutura — se um estiver fora do ar, o outro ainda responde). Sem
nenhuma das duas chaves configuradas, AI_ENABLED fica False e a home nem
tenta gerar nada — o painel simplesmente não aparece.
"""
import json
import os

import httpx
from django.utils import timezone

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
AI_ENABLED = bool(GEMINI_API_KEY or GROQ_API_KEY)

PROMPT_INSTRUCTIONS = """\
Você é o coach de um app de flashcards que ensina inglês pra brasileiros \
(português → inglês). Vou te passar um resumo em JSON do progresso recente \
de um aluno. Responda SOMENTE um JSON válido, sem markdown e sem texto \
antes ou depois, no formato:

{"message": "...", "focus_topic": "..."}

- "message": 1-2 frases em português, tom direto e encorajador (não \
piegas), falando com o aluno na segunda pessoa. Cite palavras ou tópicos \
específicos do resumo quando fizer sentido — nada genérico tipo "continue \
assim".
- "focus_topic": o id de um tópico do resumo que vale a pena o aluno \
revisar agora (ou "" se nenhum se destaca).

Resumo do aluno:
"""


SESSION_PROMPT_INSTRUCTIONS = """\
Você é o coach de um app de flashcards que ensina inglês pra brasileiros \
(português → inglês). O aluno acabou de terminar UMA rodada de estudo. \
Vou te passar as respostas dessa rodada. Responda SOMENTE um JSON válido, \
sem markdown, no formato:

{"message": "..."}

- "message": 1 a 3 frases curtas em português brasileiro, tom direto e \
específico. Comente o que aconteceu NESSA rodada em particular: cite \
palavras específicas que o aluno errou, aponte padrão se existir \
(ex: "os três erros foram verbos"), e dê uma dica prática se fizer \
sentido. Nunca diga só "bom trabalho" ou frases motivacionais vazias — \
se não tiver nada útil a dizer, comente uma coisa concreta que aconteceu. \
Fale com o aluno na segunda pessoa.

Rodada:
"""


def _build_summary(user):
    from .models import Progress, SRS_MAX_LEVEL  # import local pra evitar ciclo

    now = timezone.now()
    rows = list(
        Progress.objects.filter(user=user)
        .select_related("word", "word__topic")
        .order_by("-updated_at")[:60]
    )
    recent_wrong = [
        {"pt": p.word.pt, "en": p.word.en, "topic": p.word.topic.name, "voce_escreveu": p.last_wrong_answer}
        for p in rows if p.last_wrong_answer
    ][:10]
    mastered = sum(1 for p in rows if p.level >= SRS_MAX_LEVEL)
    overdue = sum(1 for p in rows if p.next_review <= now)
    topics_touched = sorted({p.word.topic.name for p in rows})
    return {
        "palavras_estudadas_recentemente": len(rows),
        "dominadas_nesse_recorte": mastered,
        "revisoes_vencidas_agora": overdue,
        "topicos_recentes": topics_touched,
        "ultimos_erros": recent_wrong,
    }


def _call_gemini(prompt):
    if not GEMINI_API_KEY:
        return None
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    )
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        resp = httpx.post(url, json=body, timeout=15)
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    except (httpx.HTTPError, KeyError, IndexError):
        return None


def _call_groq(prompt):
    if not GROQ_API_KEY:
        return None
    try:
        resp = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.6,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except (httpx.HTTPError, KeyError, IndexError):
        return None


def _parse_reply(text):
    if not text:
        return None
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    message = (data.get("message") or "").strip()
    if not message:
        return None
    return {"message": message, "focus_topic": (data.get("focus_topic") or "").strip()}


def generate_feedback(user):
    """None se IA desligada ou as duas chamadas falharem."""
    if not AI_ENABLED:
        return None
    prompt = PROMPT_INSTRUCTIONS + json.dumps(_build_summary(user), ensure_ascii=False)
    reply = _call_gemini(prompt) or _call_groq(prompt)
    return _parse_reply(reply)


def generate_session_feedback(session_data):
    """Comentário específico sobre uma rodada de estudo que acabou de terminar.
    session_data: {"topic": "...", "answers": [{"pt","en","typed","result"}]}
    Retorna {"message": "..."} ou None."""
    if not AI_ENABLED:
        return None
    prompt = SESSION_PROMPT_INSTRUCTIONS + json.dumps(session_data, ensure_ascii=False)
    reply = _call_gemini(prompt) or _call_groq(prompt)
    parsed = _parse_reply(reply)
    if not parsed:
        return None
    return {"message": parsed["message"]}
