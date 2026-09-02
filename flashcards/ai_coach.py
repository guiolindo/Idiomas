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
Você é um professor de inglês avaliando um aluno brasileiro que estuda \
por um app de flashcards (português → inglês). Vou te passar um JSON \
com o histórico dele: nível CEFR atual, palavras dominadas, revisões \
vencidas, tópicos tocados, últimos erros específicos.

Responda SOMENTE um JSON válido, sem markdown, no formato:

{"strengths": "...", "focus": "...", "recommendation": "...", "focus_topic": ""}

Tom: professional, específico, direto. Segunda pessoa ("você"). Português \
brasileiro. NUNCA use frases motivacionais genéricas como "continue \
assim", "bom trabalho", "você está indo bem". Só afirmações concretas \
baseadas no resumo.

Cada campo é uma frase (máximo duas), curta:
- "strengths": o que dá pra afirmar que ele domina bem, citando categoria \
ou padrão específico ("substantivos concretos", "vocabulário de família"). \
Se não tiver evidência, seja honesto: "ainda pouco material pra afirmar".
- "focus": o padrão de erro mais claro — cite palavras ou tipos ("os erros \
foram grafia de verbos irregulares", "confunde 'much'/'many'"). Se não \
houver erros no resumo, comente o gap de cobertura.
- "recommendation": UMA ação concreta pra próxima sessão — tópico \
específico, tipo de exercício, ou uma técnica ("hoje foca só nas 3 \
vencidas de <tópico>", "revise verbos antes de novos substantivos").
- "focus_topic": id do tópico que ele deveria estudar hoje (ou "").

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
    from .levels import compute_level

    now = timezone.now()
    all_progress = Progress.objects.filter(user=user).select_related("word", "word__topic")
    total_mastered = all_progress.filter(level__gte=SRS_MAX_LEVEL).count()
    level = compute_level(total_mastered)
    rows = list(all_progress.order_by("-updated_at")[:80])
    recent_wrong = [
        {"pt": p.word.pt, "en": p.word.en, "topic": p.word.topic.name, "voce_escreveu": p.last_wrong_answer}
        for p in rows if p.last_wrong_answer
    ][:15]
    overdue = sum(1 for p in rows if p.next_review <= now)
    topics_touched = sorted({p.word.topic.name for p in rows})
    return {
        "nivel_cefr_atual": level["code"],
        "descritor_nivel": level["label"],
        "palavras_dominadas_total": total_mastered,
        "faltam_pro_proximo_nivel": level["to_next"],
        "palavras_estudadas_recentemente": len(rows),
        "revisoes_vencidas_agora": overdue,
        "topicos_recentes": topics_touched,
        "ultimos_erros": recent_wrong,
    }


import logging

logger = logging.getLogger(__name__)


def _call_gemini(prompt):
    if not GEMINI_API_KEY:
        return None
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-3.5-flash:generateContent?key={GEMINI_API_KEY}"
    )
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        resp = httpx.post(url, json=body, timeout=15)
        if resp.status_code != 200:
            logger.warning("Gemini %s: %s", resp.status_code, resp.text[:200])
            return None
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    except (httpx.HTTPError, KeyError, IndexError) as e:
        logger.warning("Gemini call failed: %s", e)
        return None


def _call_groq(prompt):
    if not GROQ_API_KEY:
        return None
    try:
        resp = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                # gpt-oss-20b é o modelo generalista mais atual disponível no
                # Groq free tier — llama 3.1 8b foi descontinuado, 3.3 70b não
                # está mais disponível em algumas contas.
                "model": "openai/gpt-oss-20b",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.6,
            },
            timeout=15,
        )
        if resp.status_code != 200:
            logger.warning("Groq %s: %s", resp.status_code, resp.text[:200])
            return None
        return resp.json()["choices"][0]["message"]["content"]
    except (httpx.HTTPError, KeyError, IndexError) as e:
        logger.warning("Groq call failed: %s", e)
        return None


def _extract_json(text):
    """Retorna dict parseado a partir de texto que pode vir com prosa/markdown."""
    if not text:
        return None
    text = text.strip()
    for prefix in ("```json", "```"):
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
    if text.endswith("```"):
        text = text[:-3].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            logger.warning("_extract_json: sem JSON parseável: %r", text[:200])
            return None
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            logger.warning("_extract_json: JSON balanceado ainda inválido: %r", text[:200])
            return None


def _parse_reply(text):
    """Análise geral (home): strengths + focus + recommendation."""
    data = _extract_json(text)
    if not data:
        return None
    strengths = (data.get("strengths") or "").strip()
    focus = (data.get("focus") or "").strip()
    recommendation = (data.get("recommendation") or "").strip()
    if not any([strengths, focus, recommendation]):
        # Compat com prompt antigo que devolvia "message"
        message = (data.get("message") or "").strip()
        if not message:
            return None
        return {"strengths": "", "focus": "", "recommendation": message,
                "focus_topic": (data.get("focus_topic") or "").strip()}
    return {
        "strengths": strengths,
        "focus": focus,
        "recommendation": recommendation,
        "focus_topic": (data.get("focus_topic") or "").strip(),
    }


def _parse_session_reply(text):
    """Sessão (done screen): message curta e específica."""
    data = _extract_json(text)
    if not data:
        return None
    message = (data.get("message") or "").strip()
    if not message:
        return None
    return {"message": message}


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
    return _parse_session_reply(reply)
