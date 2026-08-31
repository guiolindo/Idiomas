import json
from datetime import timedelta

import httpx
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.core.cache import cache
from django.http import JsonResponse, HttpResponseNotAllowed
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import SignupForm
from .models import Topic, Word, Progress, Profile


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


def _known_map(user):
    """{topic_id: set(word_id sabido)}"""
    rows = Progress.objects.filter(user=user, known=True).values_list("word__topic_id", "word_id")
    out = {}
    for topic_id, word_id in rows:
        out.setdefault(topic_id, set()).add(word_id)
    return out


@login_required
def home(request):
    topics = list(Topic.objects.all())
    known_map = _known_map(request.user)
    total_words = 0
    total_known = 0
    topic_cards = []
    for t in topics:
        words = list(t.words.all())
        total = len(words)
        known = len(known_map.get(t.id, set()) & {w.id for w in words})
        total_words += total
        total_known += known
        topic_cards.append({
            "topic": t,
            "total": total,
            "known": known,
            "pct": round(known / total * 100) if total else 0,
            "done": total > 0 and known == total,
        })

    profile, _ = Profile.objects.get_or_create(user=request.user)
    overall_pct = round(total_known / total_words * 100) if total_words else 0

    # última palavra estudada (pra "continuar de onde parou")
    last_progress = Progress.objects.filter(user=request.user).order_by("-updated_at").first()
    continue_topic = last_progress.word.topic if last_progress else None

    return render(request, "flashcards/home.html", {
        "topic_cards": topic_cards,
        "total_words": total_words,
        "total_known": total_known,
        "overall_pct": overall_pct,
        "profile": profile,
        "continue_topic": continue_topic,
    })


@login_required
def study(request, slug):
    topic = get_object_or_404(Topic, slug=slug)
    words = list(topic.words.values("id", "pt", "en"))
    known_ids = set(
        Progress.objects.filter(user=request.user, known=True, word__topic=topic)
        .values_list("word_id", flat=True)
    )
    _bump_streak(request.user)
    return render(request, "flashcards/study.html", {
        "topic": topic,
        "words_json": json.dumps(words),
        "known_ids_json": json.dumps(list(known_ids)),
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
    known = request.POST.get("known") == "true"
    word = get_object_or_404(Word, id=word_id)
    if known:
        Progress.objects.update_or_create(user=request.user, word=word, defaults={"known": True})
    else:
        Progress.objects.filter(user=request.user, word=word).delete()
    return JsonResponse({"ok": True})


@login_required
def api_image(request):
    """
    Busca a foto de capa do artigo da Wikipedia sobre a palavra.

    Usamos a API de resumo da Wikipedia (não a busca da Wikimedia Commons)
    de propósito: ela devolve UM artigo já desambiguado por palavra (então
    "apple" cai na fruta, não em qualquer coisa que combine com o texto),
    e a ausência de "thumbnail" é justamente o sinal que usamos pra saber
    que a palavra não tem uma foto que faça sentido (verbos, preposições,
    conceitos abstratos etc. viram artigos de desambiguação ou não têm
    imagem de capa). A busca da Commons também vinha sendo bloqueada pela
    política antibot da Wikimedia sob volume de tráfego de app.
    """
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    q = request.GET.get("q", "").strip()
    if not q:
        return JsonResponse({"found": False})

    cache_key = f"wpsummary:{q.lower()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return JsonResponse(cached)

    headers = {
        "User-Agent": "CadernoDeIdiomas/1.0 (app pessoal de flashcards; contato: brzueira342386@gmail.com)"
    }
    title = q.strip().replace(" ", "_")
    try:
        resp = httpx.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}",
            headers=headers, timeout=8, follow_redirects=True,
        )
    except httpx.HTTPError:
        result = {"found": False}
        cache.set(cache_key, result, 60 * 60)
        return JsonResponse(result)

    data = resp.json() if resp.status_code == 200 else {}
    thumb = data.get("thumbnail")
    # "disambiguation" = página de desambiguação (ex: "use" -> lista de sentidos),
    # não uma imagem específica da palavra — tratamos como "sem foto" também.
    if resp.status_code == 200 and thumb and data.get("type") != "disambiguation":
        result = {
            "found": True,
            "url": thumb["source"],
            "page": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
            "title": data.get("title", q),
        }
    else:
        result = {"found": False}

    cache.set(cache_key, result, 60 * 60 * 24 * 7)
    return JsonResponse(result)
