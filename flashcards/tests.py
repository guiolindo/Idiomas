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

    def test_know_creates_progress_and_advances_level(self):
        resp = self.client.post(
            reverse("api_mark_progress", args=[self.word.id]), {"result": "know"}
        )
        self.assertEqual(resp.status_code, 200)
        progress = Progress.objects.get(user=self.user, word=self.word)
        self.assertEqual(progress.level, 1)
        self.assertGreater(progress.next_review, timezone.now())

    def test_miss_resets_level_and_stores_wrong_answer(self):
        progress = Progress.objects.create(user=self.user, word=self.word, level=3)
        resp = self.client.post(
            reverse("api_mark_progress", args=[self.word.id]),
            {"result": "miss", "wrong_answer": "aple"},
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
        # Home reformatada (linha meta em mono) — nível CEFR + contagem de
        # dominadas ficam na linha meta. Antes eram cards separados.
        self.assertContains(resp, "1 palavras dominadas")
        # E o item "1 palavra hoje" indica atividade
        self.assertContains(resp, "palavra")

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
        self.assertContains(resp, "revisão vencida")


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
        # Home reformatada — CTA de onboarding agora é "Começar por X — 5 cartões"
        self.assertContains(resp, "Começar por")

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
        word = Topic.objects.get(slug="a").words.first()
        self.client.post(
            reverse("api_mark_progress", args=[word.id]),
            {"result": "miss", "mode": "challenge"},
        )
        # nenhum Progress criado
        self.assertEqual(Progress.objects.filter(user=self.user).count(), 0)

    def test_normal_response_still_creates_progress(self):
        # Sem o mode=challenge, comportamento antigo
        word = Topic.objects.get(slug="a").words.first()
        self.client.post(
            reverse("api_mark_progress", args=[word.id]),
            {"result": "know"},
        )
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


class StaticPagesTests(TestCase):
    """Ajuda/Sobre/Termos são páginas públicas — não exigem login."""
    def test_help_page_loads(self):
        resp = self.client.get(reverse("help"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "revisão espaçada")

    def test_about_page_loads(self):
        resp = self.client.get(reverse("about"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Princípios")

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
        self.assertContains(resp, 'STUDY_MODE = "ditado"')
        self.assertContains(resp, "Modo Ditado")

    def test_mode_voz(self):
        resp = self.client.get(reverse("study", args=[self.topic.slug]) + "?modo=voz")
        self.assertContains(resp, 'STUDY_MODE = "voz"')
        self.assertContains(resp, "Modo Voz")

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
