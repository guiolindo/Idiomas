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

from .forms import SignupForm
from .models import Topic, Word, Progress, Profile, SRS_MAX_LEVEL
from .wikipedia import fetch_summary


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


@login_required
def home(request):
    now = timezone.now()
    topics = list(Topic.objects.all())
    mastered_map = _mastered_map(request.user)
    total_words = 0
    total_mastered = 0
    topic_cards = []
    for t in topics:
        words = list(t.words.all())
        total = len(words)
        mastered = len(mastered_map.get(t.id, set()) & {w.id for w in words})
        total_words += total
        total_mastered += mastered
        topic_cards.append({
            "topic": t,
            "total": total,
            "known": mastered,
            "pct": round(mastered / total * 100) if total else 0,
            "done": total > 0 and mastered == total,
        })

    profile, _ = Profile.objects.get_or_create(user=request.user)
    overall_pct = round(total_mastered / total_words * 100) if total_words else 0

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
        "overall_pct": overall_pct,
        "profile": profile,
        "continue_topic": continue_topic,
        "overdue_count": overdue_count,
        "overdue_topic": overdue_topic,
    })


@login_required
def study(request, slug):
    topic = get_object_or_404(Topic, slug=slug)
    now = timezone.now()
    progress_map = {
        p.word_id: p for p in Progress.objects.filter(user=request.user, word__topic=topic)
    }
    words = []
    for w in topic.words.all():
        p = progress_map.get(w.id)
        due = (p is None) or (p.next_review <= now)
        words.append({
            "id": w.id,
            "pt": w.pt,
            "en": w.en,
            "has_photo": w.has_photo,
            "photo_url": w.photo_url,
            "photo_page": w.photo_page,
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
    return JsonResponse({
        "ok": True,
        "level": progress.level,
        "mastered": progress.mastered,
        "next_review": progress.next_review.isoformat(),
    })


@login_required
def api_image(request):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    q = request.GET.get("q", "").strip()
    if not q:
        return JsonResponse({"found": False})

    cache_key = f"wpsummary:{q.lower()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return JsonResponse(cached)

    result = fetch_summary(q)
    cache.set(cache_key, result, 60 * 60 * 24 * 7)
    return JsonResponse(result)
