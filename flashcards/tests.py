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
        # Home mostra "iniciadas" (Progress existe) e "dominadas" (nivel 4)
        # como duas metricas distintas — verificar ambas.
        self.assertContains(resp, "de 2 palavras iniciadas")
        self.assertContains(resp, "1 dominadas")

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


class DailySessionCapTests(TestCase):
    """Sessão normal (respeitando SRS) tem teto — evita cair de gaveta em
    quem passa dias sem estudar. 'Praticar tudo' (?tudo=1) ignora o cap."""
    def setUp(self):
        # 40 palavras: acima do cap de 35
        words = tuple((f"pt{i}", f"en{i}") for i in range(40))
        self.topic = make_topic(words=words)
        self.user = User.objects.create_user(username="c@t.com", email="c@t.com", password="x1234567")
        self.client.login(username="c@t.com", password="x1234567")

    def test_cap_notice_appears_when_due_over_cap(self):
        # Nenhum Progress = todas 40 estão "vencidas" (novas)
        resp = self.client.get(reverse("study", args=[self.topic.slug]))
        self.assertContains(resp, "Rodada de hoje")
        # confere no JSON serializado: só 35 vêm com due=True
        due_count = resp.content.decode().count('"due": true')
        self.assertEqual(due_count, 35)

    def test_cap_ignored_when_practicing_all(self):
        resp = self.client.get(reverse("study", args=[self.topic.slug]) + "?tudo=1")
        self.assertNotContains(resp, "Rodada de hoje")
        due_count = resp.content.decode().count('"due": true')
        self.assertEqual(due_count, 40)

    def test_no_cap_when_under_threshold(self):
        # Marca 10 como dominadas: sobram 30 vencidas, abaixo do cap
        for w in self.topic.words.all()[:10]:
            Progress.objects.create(
                user=self.user, word=w, level=SRS_MAX_LEVEL,
                next_review=timezone.now() + timedelta(days=30),
            )
        resp = self.client.get(reverse("study", args=[self.topic.slug]))
        self.assertNotContains(resp, "Rodada de hoje")
