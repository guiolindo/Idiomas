import hashlib
import json
import random
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView, PasswordResetView
from django.core.cache import cache
from django.db.models import Count
from django.http import JsonResponse, HttpResponseNotAllowed
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .ai_coach import AI_ENABLED, generate_feedback, generate_session_feedback
from .forms import SignupForm
from .levels import compute_level
from .models import Topic, Word, Progress, Profile, SRS_MAX_LEVEL
from .photos import fetch_photo


def signup(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.create(user=user)
            auth_login(request, user)
            return redirect("home")
    else:
        form = SignupForm()
    return render(request, "flashcards/signup.html", {"form": form})


class IdiomasLoginView(LoginView):
    template_name = "flashcards/login.html"
    redirect_authenticated_user = True


class IdiomasLogoutView(LogoutView):
    next_page = "login"


def _client_ip(request):
    # Railway/Render ficam atrás de proxy — o IP real vem no header, não
    # em REMOTE_ADDR (que seria o IP interno do proxy).
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


class IdiomasPasswordResetView(PasswordResetView):
    """Recuperação de senha com rate limit por IP — sem isso, qualquer um
    pode martelar o formulário e spammar e-mail de reset pra qualquer
    endereço, ou tentar enumerar contas por tempo de resposta. Django já
    não revela se o e-mail existe (sempre redireciona pro mesmo "done"),
    isso aqui cobre o outro lado: volume de tentativas."""
    template_name = "flashcards/password_reset.html"
    email_template_name = "flashcards/password_reset_email.txt"
    html_email_template_name = "flashcards/password_reset_email.html"
    subject_template_name = "flashcards/password_reset_subject.txt"

    MAX_ATTEMPTS = 5
    WINDOW_SECONDS = 3600  # 1 hora

    def post(self, request, *args, **kwargs):
        ip = _client_ip(request)
        cache_key = f"pwreset:throttle:{ip}"
        count = cache.get(cache_key, 0)
        if count >= self.MAX_ATTEMPTS:
            # Mesma resposta de sucesso — não revela que foi bloqueado,
            # pra não dar pista útil a quem está tentando abusar.
            messages.info(request, "Se esse e-mail tiver uma conta, o link já foi enviado.")
            return redirect("password_reset_done")
        cache.set(cache_key, count + 1, timeout=self.WINDOW_SECONDS)
        return super().post(request, *args, **kwargs)


def _mastered_map(user):
    """{topic_id: set(word_id dominado — nível máximo do SRS)}"""
    rows = Progress.objects.filter(user=user, level__gte=SRS_MAX_LEVEL).values_list(
        "word__topic_id", "word_id"
    )
    out = {}
    for topic_id, word_id in rows:
        out.setdefault(topic_id, set()).add(word_id)
    return out


def _greeting(now):
    hour = timezone.localtime(now).hour
    if 5 <= hour < 12:
        return "Bom dia"
    if 12 <= hour < 18:
        return "Boa tarde"
    return "Boa noite"


@login_required
def home(request):
    now = timezone.now()
    topics = list(Topic.objects.all())
    mastered_map = _mastered_map(request.user)
    # todas as palavras que o aluno já viu pelo menos uma vez (Progress
    # existe) — é isso que o aluno percebe como "progresso salvo",
    # diferente de "dominada" (SRS_MAX_LEVEL) que leva semanas de revisão.
    studied_ids = set(Progress.objects.filter(user=request.user).values_list("word_id", flat=True))
    total_words = 0
    total_mastered = 0
    total_studied = 0
    topic_cards = []
    for t in topics:
        words = list(t.words.all())
        word_ids = {w.id for w in words}
        total = len(words)
        mastered = len(mastered_map.get(t.id, set()) & word_ids)
        studied = len(studied_ids & word_ids)
        total_words += total
        total_mastered += mastered
        total_studied += studied
        topic_cards.append({
            "topic": t,
            "total": total,
            "known": mastered,
            "studied": studied,
            "pct": round(studied / total * 100) if total else 0,
            "done": total > 0 and mastered == total,
        })

    # respostas dadas hoje (feedback imediato ao aluno de que o app tá
    # gravando o esforço)
    today_start = timezone.localtime(now).replace(hour=0, minute=0, second=0, microsecond=0)
    answered_today = Progress.objects.filter(user=request.user, updated_at__gte=today_start).count()

    profile, _ = Profile.objects.get_or_create(user=request.user)
    # anel mostra o quanto o aluno já *começou a estudar* (o número que
    # muda a cada palavra respondida) e não só as "dominadas", que quase
    # sempre é 0 até semanas depois de começar.
    overall_pct = round(total_studied / total_words * 100) if total_words else 0

    # Coach com IA: análise estruturada em 3 partes (strengths/focus/
    # recommendation). A home *não* regenera nada — só mostra o que já
    # foi salvo. A geração acontece no fim da sessão (api_session_coach),
    # que é o momento em que o aluno acabou de fazer algo e a análise
    # tem material novo pra referenciar. Antes a home tentava regenerar
    # a cada 1h aberta — gastava quota, produzia análise "morta" (sem
    # atividade nova), e ficava desalinhada do momento de estudo.
    ai_analysis = profile.ai_analysis or None

    # Nível CEFR computado a partir das palavras dominadas (nível 4 no SRS).
    level = compute_level(total_mastered)

    # última palavra estudada (pra "continuar de onde parou")
    last_progress = Progress.objects.filter(user=request.user).order_by("-updated_at").first()
    continue_topic = last_progress.word.topic if last_progress else None

    # revisões vencidas: cartas que já foram estudadas antes e estão devendo
    # revisão agora — não conta palavra nova (nunca estudada), só o que o
    # aluno já viu e precisa reforçar.
    overdue_qs = Progress.objects.filter(user=request.user, next_review__lte=now)
    overdue_count = overdue_qs.count()
    overdue_topic = None
    if overdue_count:
        top = (
            overdue_qs.values("word__topic")
            .annotate(n=Count("id"))
            .order_by("-n")
            .first()
        )
        if top:
            overdue_topic = Topic.objects.get(id=top["word__topic"])

    # Onboarding do dia 1: usuário sem nenhuma palavra estudada vê a home
    # como um grid vazio sem indicação clara do próximo passo. Sugerimos um
    # tópico curto pra começar (primeiro na ordem, tipicamente "básico") pra
    # transformar "abro e não sei onde clicar" em "abro e clico aí".
    is_new_user = total_studied == 0
    starter_topic = topics[0] if is_new_user and topics else None

    # Palavra do dia: 1 palavra sorteada deterministicamente por dia+usuário.
    # Reforça o ritual de abrir o app (mesmo em dia sem revisão vencida) e
    # dá exposição casual a palavras que o SRS ainda não tocou. Sem gravar
    # nada — puro conteúdo, zero fricção.
    word_of_day = _word_of_the_day(request.user, now)

    # Palavras travadas (leech) — só conta as que estão marcadas. Se houver,
    # botão discreto na home leva pra dashboard focada.
    leech_count = Progress.objects.filter(user=request.user, is_leech=True).count()

    return render(request, "flashcards/home.html", {
        "topic_cards": topic_cards,
        "total_words": total_words,
        "total_known": total_mastered,
        "total_studied": total_studied,
        "overall_pct": overall_pct,
        "profile": profile,
        "continue_topic": continue_topic,
        "overdue_count": overdue_count,
        "overdue_topic": overdue_topic,
        "ai_analysis": ai_analysis,
        "ai_enabled": AI_ENABLED,
        "ai_generated_at": profile.ai_feedback_at,
        "level": level,
        "greeting": _greeting(now),
        "first_name": (request.user.first_name or request.user.email.split("@")[0]).capitalize(),
        "answered_today": answered_today,
        "is_new_user": is_new_user,
        "starter_topic": starter_topic,
        "word_of_day": word_of_day,
        "leech_count": leech_count,
    })


def _word_of_the_day(user, now):
    """Sorteio determinístico: (user_id, data) → mesma palavra o dia inteiro,
    diferente por usuário, muda no dia seguinte. Sem tabela nova, sem
    migração — só um hash estável."""
    all_words = list(Word.objects.select_related("topic"))
    if not all_words:
        return None
    key = f"{user.id}:{timezone.localdate(now).isoformat()}"
    seed = int(hashlib.md5(key.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    return rng.choice(all_words)


@login_required
def leech_list(request):
    """Dashboard das palavras travadas — visão focada nas que erram mais.
    Serve pra o aluno reconhecer os "vilões" e ter ação direta ("praticar
    só essas")."""
    leeches = (
        Progress.objects.filter(user=request.user, is_leech=True)
        .select_related("word", "word__topic")
        .order_by("-consecutive_errors", "-updated_at")
    )
    return render(request, "flashcards/leech_list.html", {
        "leeches": leeches,
        "total": leeches.count(),
    })


CHALLENGE_SIZE = 12


@login_required
def challenge(request):
    """Modo desafio: N palavras aleatórias de tópicos variados, misturado
    fora do fluxo do SRS. Serve pra quebrar rotina e treinar reação — as
    respostas NÃO afetam next_review/level (sinalizado pelo `challenge_mode`
    no JSON, o study.js pula o POST de progresso quando ativo). O objetivo
    é ludicidade e exposição ampla, não spaced repetition."""
    all_words = list(Word.objects.select_related("topic"))
    if not all_words:
        return render(request, "flashcards/challenge.html", {"empty": True})
    picked = random.sample(all_words, min(CHALLENGE_SIZE, len(all_words)))
    words_json = json.dumps([
        {
            "id": w.id,
            "pt": w.pt,
            "en": w.en,
            "has_photo": w.has_photo,
            "photo_url": w.photo_url,
            "photo_page": w.photo_page,
            "photo_credit": w.photo_credit,
            "photo_variants": w.photo_variants or [],
            "due": True,       # todas entram na rodada
            "is_leech": False,
            "last_wrong": "",
        }
        for w in picked
    ])
    return render(request, "flashcards/challenge.html", {
        "words_json": words_json,
        "total": len(picked),
        "topic_has_photo": any(w.has_photo for w in picked),
    })


@login_required
def topic_detail(request, slug):
    """Página de "índice" do tópico: lista todas as palavras com o nível de
    progresso do aluno, sem forçar sessão de estudo. Deixa o aluno *ver* o
    que tem no tópico antes de estudar (evita a sensação de "caixa preta")."""
    topic = get_object_or_404(Topic, slug=slug)
    now = timezone.now()
    progress_map = {
        p.word_id: p for p in Progress.objects.filter(user=request.user, word__topic=topic)
    }
    rows = []
    counts = {"new": 0, "learning": 0, "due": 0, "mastered": 0}
    for w in topic.words.all():
        p = progress_map.get(w.id)
        if p is None:
            state = "new"
        elif p.level >= SRS_MAX_LEVEL:
            state = "mastered"
        elif p.next_review <= now:
            state = "due"
        else:
            state = "learning"
        counts[state] += 1
        rows.append({
            "word": w,
            "state": state,
            "level": p.level if p else 0,
            "next_review": p.next_review if p else None,
        })
    # Menor data futura de revisão pra dar o "quando libera" no estado
    # "tudo em dia" — se todas estão em revisão futura, o mais cedo que
    # algo vence é essa data.
    future_reviews = [r["next_review"] for r in rows if r["next_review"] and r["next_review"] > now]
    next_release = min(future_reviews) if future_reviews else None
    return render(request, "flashcards/topic_detail.html", {
        "topic": topic,
        "rows": rows,
        "counts": counts,
        "total": len(rows),
        "any_due": counts["new"] + counts["due"] > 0,
        "next_release": next_release,
        "now": now,
    })


# Tetos de sessão por escolha de tempo. Adaptação temporal: o aluno diz
# quanto tempo tem (3, 10 ou 20 min ≈ curto/médio/longo) e o app dimensiona
# a rodada. Sem essa opção, quem tem 3 minutos livres entra, vê 35 cartões,
# desiste e não cria hábito. Com ela, "só 3 min hoje" continua contando —
# é a diferença entre estudar todo dia e estudar quando "sobra tempo".
# "Praticar tudo" (?tudo=1) ignora completamente esses tetos.
SESSION_CAPS = {"curto": 5, "medio": 15, "longo": 35}
DEFAULT_SESSION_LENGTH = "longo"  # sem escolha explícita, mantém o teto antigo

# Modalidades de estudo — cada uma exercita um canal diferente. O usuário
# escolhe no início, e a UI se adapta. Antes ditado era uma "aba" dentro
# do estudo, o que confundia (parecia sub-opção de leitura, mas na
# verdade é outro tipo de exercício por completo — treina audição).
STUDY_MODES = {
    "escrita": {"label": "Escrita", "desc": "Vê em português, escreve em inglês"},
    "ditado":  {"label": "Ditado",  "desc": "Ouve em inglês, escreve em português"},
    "voz":     {"label": "Voz",     "desc": "Vê em português, fala em inglês"},
}
DEFAULT_STUDY_MODE = "escrita"


@login_required
def study(request, slug):
    topic = get_object_or_404(Topic, slug=slug)
    now = timezone.now()
    # ?tudo=1 = modo "praticar tudo": ignora vencimento do SRS e inclui
    # todas as palavras do tópico. Útil quando o aluno quer revisar antes
    # da hora — sem penalizar o SRS (respostas continuam sendo gravadas
    # normalmente, mas o vencimento futuro é respeitado no cálculo do
    # próximo intervalo).
    practice_all = request.GET.get("tudo") == "1"
    progress_map = {
        p.word_id: p for p in Progress.objects.filter(user=request.user, word__topic=topic)
    }
    words = []
    for w in topic.words.all():
        p = progress_map.get(w.id)
        actually_due = (p is None) or (p.next_review <= now)
        due = actually_due or practice_all
        words.append({
            "id": w.id,
            "pt": w.pt,
            "en": w.en,
            "has_photo": w.has_photo,
            "photo_url": w.photo_url,
            "photo_page": w.photo_page,
            "photo_credit": w.photo_credit,
            "photo_variants": w.photo_variants or [],
            "due": due,
            "is_leech": bool(p and p.is_leech),
            "last_wrong": p.last_wrong_answer if p else "",
            # campos internos pro cap (não vão pro JS)
            "_priority_next_review": p.next_review if p else now,
            "_priority_level": p.level if p else 0,
        })

    session_length = request.GET.get("tempo", DEFAULT_SESSION_LENGTH)
    if session_length not in SESSION_CAPS:
        session_length = DEFAULT_SESSION_LENGTH
    session_cap = SESSION_CAPS[session_length]

    study_mode = request.GET.get("modo", DEFAULT_STUDY_MODE)
    if study_mode not in STUDY_MODES:
        study_mode = DEFAULT_STUDY_MODE

    total_due = sum(1 for w in words if w["due"])
    session_capped = False
    if not practice_all and total_due > session_cap:
        # Prioriza: mais atrasado primeiro, empate desempatado por menor nível
        # (palavras mais frágeis do SRS antes das quase-dominadas).
        due_sorted = sorted(
            (w for w in words if w["due"]),
            key=lambda w: (w["_priority_next_review"], w["_priority_level"]),
        )
        keep_ids = {w["id"] for w in due_sorted[:session_cap]}
        for w in words:
            if w["due"] and w["id"] not in keep_ids:
                w["due"] = False
        session_capped = True

    # limpa campos internos antes de serializar
    for w in words:
        w.pop("_priority_next_review", None)
        w.pop("_priority_level", None)

    _bump_streak(request.user)
    return render(request, "flashcards/study.html", {
        "topic": topic,
        "words_json": json.dumps(words),
        # só mostra a opção "Foto" se pelo menos uma palavra do tópico tiver
        "topic_has_photo": any(w["has_photo"] for w in words),
        "any_due": any(w["due"] for w in words),
        "practice_all": practice_all,
        "session_capped": session_capped,
        "total_due": total_due,
        "session_cap": session_cap,
        "session_length": session_length,
        "study_mode": study_mode,
    })


def _bump_streak(user):
    profile, _ = Profile.objects.get_or_create(user=user)
    today = timezone.localdate()
    if profile.last_study_date == today:
        return
    yesterday = today - timedelta(days=1)
    profile.streak_count = profile.streak_count + 1 if profile.last_study_date == yesterday else 1
    profile.last_study_date = today
    profile.save()


@login_required
@require_POST
def api_mark_progress(request, word_id):
    result = request.POST.get("result")  # 'miss' | 'soso' | 'know'
    if result not in ("miss", "soso", "know"):
        return JsonResponse({"error": "result inválido"}, status=400)
    # Modo desafio: o cliente sinaliza que essa rodada não deve mexer no SRS
    # (é jogo, não estudo). Retornamos ok sem alterar o Progress — o aluno
    # continua tendo o feedback visual, só que sem consequência.
    if request.POST.get("mode") == "challenge":
        return JsonResponse({"ok": True, "challenge": True})
    wrong_answer = request.POST.get("wrong_answer", "")
    word = get_object_or_404(Word, id=word_id)
    progress, _ = Progress.objects.get_or_create(user=request.user, word=word)
    progress.apply_feedback(result, wrong_answer=wrong_answer)
    Profile.objects.filter(user=request.user).update(last_activity_at=timezone.now())
    return JsonResponse({
        "ok": True,
        "level": progress.level,
        "mastered": progress.mastered,
        "next_review": progress.next_review.isoformat(),
    })


@login_required
@require_POST
def api_session_coach(request):
    """Recebe o resumo de uma rodada de estudo que acabou de terminar e
    devolve um comentário curto e específico da IA. Chamado pelo study.js
    no done screen. Sem chaves de IA configuradas, devolve {"enabled": False}."""
    if not AI_ENABLED:
        return JsonResponse({"enabled": False})
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "json inválido"}, status=400)
    answers = data.get("answers") or []
    if not isinstance(answers, list) or not answers:
        return JsonResponse({"error": "answers ausente"}, status=400)
    # sanitiza: só campos previstos, limita tamanho
    clean_answers = [
        {
            "pt": str(a.get("pt", ""))[:60],
            "en": str(a.get("en", ""))[:60],
            "typed": str(a.get("typed", ""))[:60],
            "result": a.get("result") if a.get("result") in ("miss", "soso", "know") else "miss",
        }
        for a in answers[:30]
    ]
    result = generate_session_feedback({
        "topic": str(data.get("topic", ""))[:60],
        "answers": clean_answers,
    })
    # Também atualiza a análise geral (strengths/focus/recommendation)
    # aqui, no fim da sessão, em vez de deixar a home regenerar depois
    # sem contexto novo. Se a chamada falhar, mantém a análise anterior
    # (não sobrescreve com vazio).
    profile = Profile.objects.filter(user=request.user).first()
    if profile:
        analysis = generate_feedback(request.user)
        if analysis:
            profile.ai_analysis = analysis
            profile.ai_feedback = analysis.get("recommendation") or analysis.get("message", "")
            profile.ai_feedback_at = timezone.now()
            profile.save(update_fields=["ai_analysis", "ai_feedback", "ai_feedback_at"])
    if not result:
        return JsonResponse({"enabled": True, "message": ""})
    return JsonResponse({"enabled": True, "message": result["message"]})


def help_page(request):
    return render(request, "flashcards/help.html")


def about_page(request):
    return render(request, "flashcards/about.html")


def terms_page(request):
    return render(request, "flashcards/terms.html")


@login_required
def api_image(request):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    q = request.GET.get("q", "").strip()
    if not q:
        return JsonResponse({"found": False})

    cache_key = f"photo:{q.lower()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return JsonResponse(cached)

    result = fetch_photo(q)
    cache.set(cache_key, result, 60 * 60 * 24 * 7)
    return JsonResponse(result)
