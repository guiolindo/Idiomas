import json
from datetime import timedelta

from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.core.cache import cache
from django.db.models import Count
from django.http import JsonResponse, HttpResponseNotAllowed
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .ai_coach import AI_ENABLED, generate_feedback, generate_session_feedback
from .forms import SignupForm
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

    # Coach com IA: gera no máximo 1x por hora de atividade, e só se ainda
    # não gerou nada pra essa leva de atividade (evita re-chamar a IA toda
    # vez que a home é aberta). Sem chave configurada, AI_ENABLED é False e
    # isso nunca dispara — o painel some do template.
    ai_feedback = None
    if AI_ENABLED:
        should_generate = (
            profile.last_activity_at
            and now - profile.last_activity_at >= timedelta(hours=1)
            and (not profile.ai_feedback_at or profile.ai_feedback_at < profile.last_activity_at)
        )
        if should_generate:
            result = generate_feedback(request.user)
            if result:
                profile.ai_feedback = result["message"]
                profile.ai_feedback_at = now
                profile.save(update_fields=["ai_feedback", "ai_feedback_at"])
        ai_feedback = profile.ai_feedback or None

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
        "ai_feedback": ai_feedback,
        "greeting": _greeting(now),
        "first_name": (request.user.first_name or request.user.email.split("@")[0]).capitalize(),
        "answered_today": answered_today,
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
    return render(request, "flashcards/topic_detail.html", {
        "topic": topic,
        "rows": rows,
        "counts": counts,
        "total": len(rows),
        "any_due": counts["new"] + counts["due"] > 0,
    })


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
            "last_wrong": p.last_wrong_answer if p else "",
        })
    _bump_streak(request.user)
    return render(request, "flashcards/study.html", {
        "topic": topic,
        "words_json": json.dumps(words),
        # só mostra a opção "Foto" se pelo menos uma palavra do tópico tiver
        "topic_has_photo": any(w["has_photo"] for w in words),
        "any_due": any(w["due"] for w in words),
        "practice_all": practice_all,
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
    if not result:
        return JsonResponse({"enabled": True, "message": ""})
    return JsonResponse({"enabled": True, "message": result["message"]})


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
