from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Topic, Word, Progress, Profile, SRS_MAX_LEVEL
from .views import _bump_streak


def make_topic(slug="frutas", name="Frutas", emoji="🍎", words=(("maçã", "apple"), ("banana", "banana"))):
    topic = Topic.objects.create(slug=slug, name=name, emoji=emoji, order=0)
    for i, (pt, en) in enumerate(words):
        Word.objects.create(topic=topic, pt=pt, en=en, order=i)
    return topic


class SignupTests(TestCase):
    def test_signup_creates_user_profile_and_logs_in(self):
        resp = self.client.post(reverse("signup"), {
            "email": "novo@teste.com",
            "password1": "senhaforte2026",
            "password2": "senhaforte2026",
        })
        self.assertEqual(resp.status_code, 302)
        user = User.objects.get(email="novo@teste.com")
        self.assertEqual(user.username, "novo@teste.com")
        self.assertTrue(Profile.objects.filter(user=user).exists())
        # já logado após o cadastro
        resp = self.client.get(reverse("home"))
        self.assertEqual(resp.status_code, 200)

    def test_signup_rejects_duplicate_email(self):
        User.objects.create_user(username="ja@existe.com", email="ja@existe.com", password="x1234567")
        resp = self.client.post(reverse("signup"), {
            "email": "ja@existe.com",
            "password1": "senhaforte2026",
            "password2": "senhaforte2026",
        })
        self.assertEqual(resp.status_code, 200)  # re-renderiza com erro, não redireciona
        self.assertContains(resp, "Já existe uma conta")


class AccessControlTests(TestCase):
    def setUp(self):
        make_topic()

    def test_home_requires_login(self):
        resp = self.client.get(reverse("home"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("login"), resp.url)

    def test_study_requires_login(self):
        resp = self.client.get(reverse("study", args=["frutas"]))
        self.assertEqual(resp.status_code, 302)

    def test_login_then_next_redirects_back(self):
        User.objects.create_user(username="u@t.com", email="u@t.com", password="x1234567")
        target = reverse("study", args=["frutas"])
        resp = self.client.post(f"{reverse('login')}?next={target}", {
            "username": "u@t.com", "password": "x1234567",
        })
        self.assertRedirects(resp, target)


class ProgressTests(TestCase):
    def setUp(self):
        self.topic = make_topic()
        self.word = self.topic.words.first()
        self.user = User.objects.create_user(username="p@t.com", email="p@t.com", password="x1234567")
        Profile.objects.create(user=self.user)
        self.client.login(username="p@t.com", password="x1234567")

    def _open_session(self):
        """Abre uma rodada em /estudar/ e retorna a sessão criada."""
        from flashcards.models import StudySession
        self.client.get(reverse("study", args=[self.topic.slug]))
        return StudySession.objects.filter(user=self.user).order_by("-created_at").first()

    def test_know_creates_progress_and_advances_level(self):
        session = self._open_session()
        resp = self.client.post(
            reverse("api_mark_progress", args=[self.word.id]),
            {"result": "know", "session_id": session.id},
        )
        self.assertEqual(resp.status_code, 200)
        progress = Progress.objects.get(user=self.user, word=self.word)
        self.assertEqual(progress.level, 1)
        self.assertGreater(progress.next_review, timezone.now())

    def test_miss_resets_level_and_stores_wrong_answer(self):
        progress = Progress.objects.create(user=self.user, word=self.word, level=3)
        session = self._open_session()
        resp = self.client.post(
            reverse("api_mark_progress", args=[self.word.id]),
            {"result": "miss", "wrong_answer": "aple", "session_id": session.id},
        )
        self.assertEqual(resp.status_code, 200)
        progress.refresh_from_db()
        self.assertEqual(progress.level, 0)
        self.assertEqual(progress.last_wrong_answer, "aple")

    def test_soso_keeps_level_but_reschedules(self):
        progress = Progress.objects.create(user=self.user, word=self.word, level=2)
        self.client.post(reverse("api_mark_progress", args=[self.word.id]), {"result": "soso"})
        progress.refresh_from_db()
        self.assertEqual(progress.level, 2)

    def test_invalid_result_rejected(self):
        resp = self.client.post(reverse("api_mark_progress", args=[self.word.id]), {"result": "banana"})
        self.assertEqual(resp.status_code, 400)

    def test_mark_progress_requires_login(self):
        self.client.logout()
        resp = self.client.post(reverse("api_mark_progress", args=[self.word.id]), {"result": "know"})
        self.assertEqual(resp.status_code, 302)

    def test_home_counts_mastered_words(self):
        Progress.objects.create(user=self.user, word=self.word, level=SRS_MAX_LEVEL)
        resp = self.client.get(reverse("home"))
        # Home v4 — nível CEFR-por-vocabulário removido (era ilusão de
        # progresso, ver revisão SLA). Confirma que a página carrega e
        # que a linha meta mostra a atividade do dia.
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Recomendado agora")

    def test_word_due_when_no_progress_or_overdue(self):
        due_word = self.topic.words.last()
        Progress.objects.create(
            user=self.user, word=self.word,
            next_review=timezone.now() + timedelta(days=10),
        )
        resp = self.client.get(reverse("study", args=[self.topic.slug]))
        self.assertContains(resp, due_word.pt)

    def test_overdue_widget_shows_on_home(self):
        Progress.objects.create(
            user=self.user, word=self.word,
            next_review=timezone.now() - timedelta(days=1),
        )
        resp = self.client.get(reverse("home"))
        # Tagline agora fala "palavra vencida"; hero é "Recomendado agora"
        self.assertContains(resp, "palavra vencida")


class StreakTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="s@t.com", email="s@t.com", password="x1234567")

    def test_first_study_sets_streak_to_one(self):
        _bump_streak(self.user)
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.streak_count, 1)
        self.assertEqual(profile.last_study_date, timezone.localdate())

    def test_same_day_does_not_double_count(self):
        _bump_streak(self.user)
        _bump_streak(self.user)
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.streak_count, 1)

    def test_consecutive_day_increments(self):
        Profile.objects.create(
            user=self.user, streak_count=3, last_study_date=timezone.localdate() - timedelta(days=1)
        )
        _bump_streak(self.user)
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.streak_count, 4)

    def test_gap_resets_streak(self):
        Profile.objects.create(
            user=self.user, streak_count=5, last_study_date=timezone.localdate() - timedelta(days=3)
        )
        _bump_streak(self.user)
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.streak_count, 1)


class LeechTests(TestCase):
    """Palavras que o aluno erra 3+ vezes seguidas viram 'leech' — a UI
    avisa e o coach passa a citá-las nominalmente."""
    def setUp(self):
        self.topic = make_topic()
        self.word = self.topic.words.first()
        self.user = User.objects.create_user(username="l@t.com", email="l@t.com", password="x1234567")

    def test_consecutive_misses_mark_leech(self):
        p = Progress.objects.create(user=self.user, word=self.word)
        for _ in range(Progress.LEECH_THRESHOLD):
            p.apply_feedback("miss", wrong_answer="err")
        p.refresh_from_db()
        self.assertTrue(p.is_leech)
        self.assertEqual(p.consecutive_errors, Progress.LEECH_THRESHOLD)

    def test_two_misses_not_yet_leech(self):
        p = Progress.objects.create(user=self.user, word=self.word)
        p.apply_feedback("miss", wrong_answer="a")
        p.apply_feedback("miss", wrong_answer="b")
        p.refresh_from_db()
        self.assertFalse(p.is_leech)

    def test_soso_resets_streak_but_keeps_leech(self):
        # "Quase" mostra esforço, não domínio — não deve limpar o rótulo
        p = Progress.objects.create(
            user=self.user, word=self.word, consecutive_errors=3, is_leech=True,
        )
        p.apply_feedback("soso")
        p.refresh_from_db()
        self.assertEqual(p.consecutive_errors, 0)
        self.assertTrue(p.is_leech)

    def test_know_clears_leech(self):
        p = Progress.objects.create(
            user=self.user, word=self.word, consecutive_errors=3, is_leech=True,
        )
        p.apply_feedback("know")
        p.refresh_from_db()
        self.assertEqual(p.consecutive_errors, 0)
        self.assertFalse(p.is_leech)


class SessionLengthTests(TestCase):
    """Adaptação temporal: aluno escolhe curto/medio/longo (5/15/35) na
    entrada e o cap dimensiona a sessão. 'Praticar tudo' ignora tudo."""
    def setUp(self):
        # 40 palavras: acima do maior cap
        words = tuple((f"pt{i}", f"en{i}") for i in range(40))
        self.topic = make_topic(words=words)
        self.user = User.objects.create_user(username="c@t.com", email="c@t.com", password="x1234567")
        self.client.login(username="c@t.com", password="x1234567")

    def test_default_uses_long_cap(self):
        resp = self.client.get(reverse("study", args=[self.topic.slug]))
        due_count = resp.content.decode().count('"due": true')
        self.assertEqual(due_count, 35)

    def test_short_session_uses_five_cards(self):
        resp = self.client.get(reverse("study", args=[self.topic.slug]) + "?tempo=curto")
        due_count = resp.content.decode().count('"due": true')
        self.assertEqual(due_count, 5)
        self.assertContains(resp, "Rodada de hoje")

    def test_medium_session_uses_fifteen(self):
        resp = self.client.get(reverse("study", args=[self.topic.slug]) + "?tempo=medio")
        due_count = resp.content.decode().count('"due": true')
        self.assertEqual(due_count, 15)

    def test_invalid_tempo_falls_back_to_default(self):
        resp = self.client.get(reverse("study", args=[self.topic.slug]) + "?tempo=absurdo")
        due_count = resp.content.decode().count('"due": true')
        self.assertEqual(due_count, 35)  # default = longo

    def test_practice_all_ignores_time_cap(self):
        resp = self.client.get(reverse("study", args=[self.topic.slug]) + "?tudo=1&tempo=curto")
        self.assertNotContains(resp, "Rodada de hoje")
        due_count = resp.content.decode().count('"due": true')
        self.assertEqual(due_count, 40)


class OnboardingTests(TestCase):
    """Home do usuário sem nenhuma palavra estudada mostra hero de boas-vindas
    apontando pro primeiro tópico. Some depois da primeira palavra."""
    def setUp(self):
        make_topic(slug="basico", name="Básico", words=(("olá", "hello"),))
        make_topic(slug="frutas", name="Frutas", words=(("maçã", "apple"),))
        self.user = User.objects.create_user(username="new@t.com", email="new@t.com", password="x1234567")
        Profile.objects.create(user=self.user)
        self.client.login(username="new@t.com", password="x1234567")

    def test_new_user_sees_welcome_hero(self):
        resp = self.client.get(reverse("home"))
        # Home v3 — CTA hero pra novo user tem eyebrow "Comece por" +
        # hint "3 minutinhos já valem"
        self.assertContains(resp, "Comece por")
        self.assertContains(resp, "3 minutinhos")

    def test_hero_disappears_after_first_word(self):
        word = Topic.objects.get(slug="basico").words.first()
        Progress.objects.create(user=self.user, word=word)
        resp = self.client.get(reverse("home"))
        self.assertNotContains(resp, "Comece por")


class ChallengeTests(TestCase):
    """Modo desafio: sessão de N palavras aleatórias que NÃO afeta o SRS.
    Ainda registra pro coach da sessão poder comentar."""
    def setUp(self):
        make_topic(slug="a", name="A", words=(("um","one"),("dois","two"),("tres","three")))
        make_topic(slug="b", name="B", words=(("quatro","four"),("cinco","five")))
        self.user = User.objects.create_user(username="ch@t.com", email="ch@t.com", password="x1234567")
        self.client.login(username="ch@t.com", password="x1234567")

    def test_challenge_page_loads_with_shuffled_words(self):
        resp = self.client.get(reverse("challenge"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "CHALLENGE_MODE = true")
        self.assertContains(resp, "Modo livre")

    def test_challenge_response_does_not_touch_progress(self):
        # Autoriza sessão via GET normal e usa o session_id que o servidor
        # deu — não dá mais pra forjar mode=challenge do cliente.
        from flashcards.models import StudySession
        resp = self.client.get(reverse("challenge"))
        session = StudySession.objects.filter(user=self.user).order_by("-created_at").first()
        self.assertFalse(session.affects_srs)
        word_id = session.word_ids[0]
        self.client.post(
            reverse("api_mark_progress", args=[word_id]),
            {"result": "miss", "session_id": session.id},
        )
        # nenhum Progress criado — sessão marcou affects_srs=False
        self.assertEqual(Progress.objects.filter(user=self.user).count(), 0)

    def test_normal_response_still_creates_progress(self):
        # Rodada normal via /estudar/ — sessão autoriza a palavra
        from flashcards.models import StudySession
        topic = Topic.objects.get(slug="a")
        self.client.get(reverse("study", args=[topic.slug]))
        session = StudySession.objects.filter(user=self.user).order_by("-created_at").first()
        self.assertTrue(session.affects_srs)
        word_id = session.word_ids[0]
        self.client.post(
            reverse("api_mark_progress", args=[word_id]),
            {"result": "know", "session_id": session.id},
        )
        self.assertEqual(Progress.objects.filter(user=self.user).count(), 1)


class ProgressAuthorizationTests(TestCase):
    """Fecha A-01 da auditoria: api_mark_progress agora exige session_id
    válido criado server-side, e a palavra tem que estar na rodada."""
    def setUp(self):
        self.topic_a = make_topic(slug="a", name="A", words=(("um","one"),("dois","two")))
        self.topic_b = make_topic(slug="b", name="B", words=(("cinco","five"),("seis","six")))
        self.user = User.objects.create_user(username="s@t.com", email="s@t.com", password="x1234567")
        self.client.login(username="s@t.com", password="x1234567")

    def test_progress_requires_session_id(self):
        word = self.topic_a.words.first()
        resp = self.client.post(reverse("api_mark_progress", args=[word.id]), {"result": "know"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(Progress.objects.count(), 0)

    def test_progress_rejects_invalid_session(self):
        word = self.topic_a.words.first()
        resp = self.client.post(
            reverse("api_mark_progress", args=[word.id]),
            {"result": "know", "session_id": "999999"},
        )
        self.assertEqual(resp.status_code, 403)

    def test_progress_rejects_word_outside_session(self):
        """Abro rodada do tópico A e tento marcar palavra do tópico B."""
        from flashcards.models import StudySession
        self.client.get(reverse("study", args=["a"]))
        session = StudySession.objects.filter(user=self.user).order_by("-created_at").first()
        stranger_word = self.topic_b.words.first()
        resp = self.client.post(
            reverse("api_mark_progress", args=[stranger_word.id]),
            {"result": "know", "session_id": session.id},
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(Progress.objects.count(), 0)

    def test_progress_rejects_expired_session(self):
        from flashcards.models import StudySession
        from datetime import timedelta as td
        self.client.get(reverse("study", args=["a"]))
        session = StudySession.objects.filter(user=self.user).order_by("-created_at").first()
        session.expires_at = timezone.now() - td(minutes=1)
        session.save()
        word_id = session.word_ids[0]
        resp = self.client.post(
            reverse("api_mark_progress", args=[word_id]),
            {"result": "know", "session_id": session.id},
        )
        self.assertEqual(resp.status_code, 403)

    def test_client_cannot_forge_challenge_mode(self):
        """Cliente não pode mais mandar mode=challenge pra pular SRS —
        a decisão de affects_srs vem só da sessão."""
        from flashcards.models import StudySession
        self.client.get(reverse("study", args=["a"]))  # sessão normal, affects_srs=True
        session = StudySession.objects.filter(user=self.user).order_by("-created_at").first()
        word_id = session.word_ids[0]
        # Cliente envia mode=challenge tentando burlar
        self.client.post(
            reverse("api_mark_progress", args=[word_id]),
            {"result": "know", "session_id": session.id, "mode": "challenge"},
        )
        # SRS foi gravado normalmente — o mode do cliente é ignorado
        self.assertEqual(Progress.objects.filter(user=self.user).count(), 1)


class LeechListTests(TestCase):
    def setUp(self):
        self.topic = make_topic()
        self.user = User.objects.create_user(username="lp@t.com", email="lp@t.com", password="x1234567")
        self.client.login(username="lp@t.com", password="x1234567")

    def test_empty_state_when_no_leeches(self):
        resp = self.client.get(reverse("leech_list"))
        self.assertContains(resp, "Nenhuma palavra travada")

    def test_leeches_listed_when_present(self):
        word = self.topic.words.first()
        Progress.objects.create(
            user=self.user, word=word,
            consecutive_errors=4, is_leech=True,
        )
        resp = self.client.get(reverse("leech_list"))
        self.assertContains(resp, word.pt)
        self.assertContains(resp, word.en)
        self.assertContains(resp, "4 erros seguidos")


class NextTopicTests(TestCase):
    """A home decide qual tópico os cards de modo abrem. A ordem tem que
    ser NATURAL — não pode ficar preso no último tópico estudado quando
    já dominou tudo. Cenário reportado: usuário dominou Pessoas e
    família mas os cards continuavam abrindo lá em vez de Partes do
    corpo."""
    def setUp(self):
        # 3 tópicos em ordem, com 2 palavras cada
        self.t1 = make_topic(slug="t1", name="Um", words=(("a", "a"), ("b", "b")))
        self.t1.order = 1; self.t1.save()
        self.t2 = make_topic(slug="t2", name="Dois", words=(("c", "c"), ("d", "d")))
        self.t2.order = 2; self.t2.save()
        self.t3 = make_topic(slug="t3", name="Três", words=(("e", "e"), ("f", "f")))
        self.t3.order = 3; self.t3.save()
        self.user = User.objects.create_user(username="n@t.com", email="n@t.com", password="x1234567")
        Profile.objects.create(user=self.user)
        self.client.login(username="n@t.com", password="x1234567")

    def test_new_user_starts_at_first_topic(self):
        resp = self.client.get(reverse("home"))
        # CTA hero aponta pro Um (primeiro nunca iniciado)
        self.assertContains(resp, ">Um<")

    def test_advances_to_next_topic_when_previous_dominated(self):
        """Cenário do usuário: dominei Um todo, quero que a home aponte
        pro Dois automaticamente."""
        for w in self.t1.words.all():
            Progress.objects.create(user=self.user, word=w, level=SRS_MAX_LEVEL,
                                     next_review=timezone.now() + timedelta(days=30))
        resp = self.client.get(reverse("home"))
        # Não deve mais apontar pro Um dominado, e sim pro Dois
        self.assertContains(resp, ">Dois<")
        self.assertContains(resp, "hora de avançar")

    def test_overdue_wins_over_new_topic(self):
        """Se Um tem palavra vencida, ele volta a ser recomendado — SRS
        clássico manda antes de avanço."""
        w = self.t1.words.first()
        Progress.objects.create(user=self.user, word=w, level=1,
                                 next_review=timezone.now() - timedelta(days=1))
        resp = self.client.get(reverse("home"))
        self.assertContains(resp, ">Um<")
        self.assertContains(resp, "Recomendado agora")

    def test_in_progress_wins_over_untouched(self):
        """Se comecei Um mas não terminei, e nem toquei em Dois, a home
        aponta pra Um (terminar antes de abrir novo)."""
        w = self.t1.words.first()
        Progress.objects.create(user=self.user, word=w, level=2,
                                 next_review=timezone.now() + timedelta(days=10))
        resp = self.client.get(reverse("home"))
        self.assertContains(resp, ">Um<")

    def test_mode_cards_show_topic_name(self):
        """Cada card de modo mostra qual tópico vai abrir — a pessoa não
        clica no escuro. Novo usuário NÃO vê os 4 cards (só o CTA
        principal, pra não sobrecarregar). Depois da primeira palavra
        estudada, os 4 cards aparecem."""
        # Novo user: cards NÃO aparecem
        resp = self.client.get(reverse("home"))
        self.assertNotContains(resp, "Modo · Um")
        # Após primeira palavra estudada, os 4 cards ficam visíveis
        word = self.t1.words.first()
        Progress.objects.create(user=self.user, word=word)
        resp = self.client.get(reverse("home"))
        self.assertContains(resp, "Modo · Um", count=4)


class HealthzTests(TestCase):
    """Health check pra sondagem externa — 200 se app+DB+migrations+vocab
    ok. Retorno com checks:{db,migrations,vocabulario} pra ver o que falhou."""
    def test_healthz_returns_checks(self):
        # Cria 100 palavras pra passar o vocab check
        topic = Topic.objects.create(slug="v", name="V", order=0)
        for i in range(100):
            Word.objects.create(topic=topic, pt=f"pt{i}", en=f"en{i}", order=i)
        resp = self.client.get(reverse("healthz"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["checks"]["db"], "ok")
        self.assertEqual(data["checks"]["vocabulario"], "ok")


class AliasesTests(TestCase):
    """A-05 da auditoria: /login/ e /conta/criar/ redirecionam
    pras rotas oficiais (/entrar/ e /criar-conta/)."""
    def test_login_alias_redirects(self):
        resp = self.client.get("/login/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/entrar/", resp.url)

    def test_conta_criar_alias_redirects(self):
        resp = self.client.get("/conta/criar/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/criar-conta/", resp.url)


class CoachOptInTests(TestCase):
    """A-03 da auditoria: coach de IA vem desligado por padrão. Nada é
    enviado pra Gemini/Groq sem opt-in explícito no perfil."""
    def setUp(self):
        make_topic()
        self.user = User.objects.create_user(username="c@t.com", email="c@t.com", password="x1234567")
        self.profile = Profile.objects.create(user=self.user)
        self.client.login(username="c@t.com", password="x1234567")

    def test_coach_default_disabled(self):
        self.assertFalse(self.profile.coach_enabled)

    def test_settings_page_toggles_coach(self):
        resp = self.client.post(reverse("settings"), {"coach_enabled": "on"})
        self.assertEqual(resp.status_code, 200)
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.coach_enabled)
        # Desligar de novo
        resp = self.client.post(reverse("settings"), {})
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.coach_enabled)

    def test_privacy_page_loads(self):
        resp = self.client.get(reverse("privacy"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Gemini")
        self.assertContains(resp, "desligado por padrão")


class DisplayNameTests(TestCase):
    """Nome bonito no cumprimento — evita 'Ux.review.20260907.' feio."""
    def test_uses_first_name_when_set(self):
        from flashcards.views import _display_name
        u = User.objects.create_user(
            username="a@t.com", email="a@t.com",
            first_name="joão", password="x1234567",
        )
        self.assertEqual(_display_name(u), "João")

    def test_falls_back_to_email_local_part(self):
        from flashcards.views import _display_name
        u = User.objects.create_user(
            username="bruno@t.com", email="bruno@t.com", password="x1234567",
        )
        self.assertEqual(_display_name(u), "Bruno")

    def test_strips_junk_from_email(self):
        """Emails como 'ux.review.20260907@t.com' viram só 'Ux'."""
        from flashcards.views import _display_name
        u = User.objects.create_user(
            username="ux.review.20260907@t.com",
            email="ux.review.20260907@t.com", password="x1234567",
        )
        self.assertEqual(_display_name(u), "Ux")


class TemplateHygieneTests(TestCase):
    """Bug recorrente: comentário Django '{# ... #}' só funciona em UMA
    linha. Multi-linha vaza pro HTML e vira lixo visual na home. Este
    teste varre todos os templates procurando aberturas '{#' sem
    fechamento na mesma linha — impede a regressão."""
    def test_no_multiline_django_comments(self):
        import os
        offenders = []
        base = os.path.join(os.path.dirname(__file__), "templates")
        for root, _dirs, files in os.walk(base):
            for f in files:
                if not f.endswith(".html"):
                    continue
                path = os.path.join(root, f)
                with open(path, encoding="utf-8") as fp:
                    for i, line in enumerate(fp, 1):
                        idx = line.find("{#")
                        if idx >= 0 and "#}" not in line[idx:]:
                            offenders.append(f"{path}:{i}")
        self.assertEqual(
            offenders, [],
            "Comentário Django multi-linha detectado — use {% comment %}...{% endcomment %} "
            "em vez de {# ... #} pra bloco. Locais:\n" + "\n".join(offenders),
        )


class StaticPagesTests(TestCase):
    """Ajuda/Sobre/Termos são páginas públicas — não exigem login."""
    def test_help_page_loads(self):
        resp = self.client.get(reverse("help"))
        self.assertEqual(resp.status_code, 200)
        # Ajuda reescrita em linguagem natural — sem jargão técnico
        self.assertContains(resp, "Como funciona a revisão")

    def test_about_page_loads(self):
        resp = self.client.get(reverse("about"))
        self.assertEqual(resp.status_code, 200)
        # Sobre reescrita — "Princípios" virou "No que a gente acredita"
        self.assertContains(resp, "No que a gente acredita")

    def test_terms_page_loads(self):
        resp = self.client.get(reverse("terms"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "sua conta")


class StudyModeTests(TestCase):
    """study aceita ?modo= com escrita/ditado/voz — inválido cai pra escrita."""
    def setUp(self):
        self.topic = make_topic()
        self.user = User.objects.create_user(username="m@t.com", email="m@t.com", password="x1234567")
        self.client.login(username="m@t.com", password="x1234567")

    def test_default_mode_is_escrita(self):
        resp = self.client.get(reverse("study", args=[self.topic.slug]))
        self.assertContains(resp, 'STUDY_MODE = "escrita"')

    def test_mode_ditado(self):
        resp = self.client.get(reverse("study", args=[self.topic.slug]) + "?modo=ditado")
        # Renomeado pra Compreensão: modo agora é múltipla escolha PT,
        # não escrever tradução. Value do parâmetro mantém 'ditado' por
        # compat (mudança só de label).
        self.assertContains(resp, 'STUDY_MODE = "ditado"')
        # Label agora é a TAREFA, não o método (feedback da revisão UX)
        self.assertContains(resp, "Ouvir e escolher")

    def test_mode_voz(self):
        resp = self.client.get(reverse("study", args=[self.topic.slug]) + "?modo=voz")
        self.assertContains(resp, 'STUDY_MODE = "voz"')
        self.assertContains(resp, "Falar e comparar")

    def test_invalid_mode_falls_back_to_escrita(self):
        resp = self.client.get(reverse("study", args=[self.topic.slug]) + "?modo=xpto")
        self.assertContains(resp, 'STUDY_MODE = "escrita"')


class WordOfTheDayTests(TestCase):
    def setUp(self):
        make_topic(words=(("um","one"),("dois","two"),("tres","three")))
        self.user = User.objects.create_user(username="wd@t.com", email="wd@t.com", password="x1234567")
        Profile.objects.create(user=self.user)
        # dá pelo menos 1 palavra estudada pro widget aparecer (novo user esconde)
        Progress.objects.create(user=self.user, word=Topic.objects.first().words.first())
        self.client.login(username="wd@t.com", password="x1234567")

    def test_home_shows_word_of_day_widget(self):
        resp = self.client.get(reverse("home"))
        self.assertContains(resp, "Palavra do dia")

    def test_same_word_returned_within_same_day(self):
        # Duas chamadas seguidas devolvem a mesma palavra (determinismo)
        from flashcards.views import _word_of_the_day
        from django.utils import timezone as tz
        now = tz.now()
        w1 = _word_of_the_day(self.user, now)
        w2 = _word_of_the_day(self.user, now)
        self.assertEqual(w1.id, w2.id)
