from django.conf import settings
from django.db import models
from django.utils import timezone

# Intervalos do Leitner leve (em dias), por nível/caixa. Nível 0 = acabou de
# errar ou é novo; nível máximo = bem consolidado.
SRS_INTERVALS_DAYS = [1, 3, 7, 15, 30]
SRS_MAX_LEVEL = len(SRS_INTERVALS_DAYS) - 1


class Topic(models.Model):
    slug = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=80)
    emoji = models.CharField(max_length=16)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    @property
    def word_count(self):
        return self.words.count()


class Word(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="words")
    pt = models.CharField("português", max_length=80)
    en = models.CharField("inglês", max_length=80)
    order = models.PositiveIntegerField(default=0)
    has_photo = models.BooleanField(
        "tem foto que faz sentido",
        default=True,
        help_text="Desmarque para palavras abstratas (verbos, preposições, "
                   "conceitos) onde uma foto não ajuda — o modo Foto nem "
                   "aparece pro aluno nesses casos.",
    )
    photo_url = models.URLField("foto", max_length=500, blank=True, default="")
    photo_page = models.URLField("página de origem da foto", max_length=500, blank=True, default="")
    photo_credit = models.CharField("crédito da foto", max_length=120, blank=True, default="")

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.pt} → {self.en}"


class Progress(models.Model):
    """
    Repetição espaçada leve (Leitner): cada acerto avança uma caixa e
    empurra a próxima revisão mais pra frente; cada erro volta pra caixa 0.
    "Quase" (acertou com esforço) mantém a caixa, só reagenda pra amanhã —
    reforça sem fingir que já está consolidado.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="progress")
    word = models.ForeignKey(Word, on_delete=models.CASCADE, related_name="progress")
    level = models.PositiveSmallIntegerField(default=0)
    next_review = models.DateTimeField(default=timezone.now, db_index=True)
    last_wrong_answer = models.CharField(max_length=100, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "word")
        verbose_name_plural = "progress"

    def __str__(self):
        return f"{self.user} · {self.word} · nível {self.level}"

    @property
    def mastered(self):
        return self.level >= SRS_MAX_LEVEL

    def apply_feedback(self, result: str, wrong_answer: str = ""):
        """result: 'miss' | 'soso' | 'know'"""
        now = timezone.now()
        if result == "miss":
            self.level = 0
            self.next_review = now + timezone.timedelta(days=SRS_INTERVALS_DAYS[0])
            self.last_wrong_answer = wrong_answer[:100]
        elif result == "soso":
            self.next_review = now + timezone.timedelta(days=1)
            self.last_wrong_answer = ""
        else:  # know
            self.level = min(self.level + 1, SRS_MAX_LEVEL)
            self.next_review = now + timezone.timedelta(days=SRS_INTERVALS_DAYS[self.level])
            self.last_wrong_answer = ""
        self.save()


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    streak_count = models.PositiveIntegerField(default=0)
    last_study_date = models.DateField(null=True, blank=True)

    # Coach com IA: última vez que o aluno respondeu algo, e o feedback
    # gerado a partir disso (gerado no máximo 1x por hora de atividade —
    # ver flashcards/ai_coach.py). Fica vazio/desligado sem GEMINI_API_KEY
    # ou GROQ_API_KEY configuradas.
    last_activity_at = models.DateTimeField(null=True, blank=True)
    ai_feedback = models.TextField(blank=True, default="")
    ai_feedback_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Perfil de {self.user}"
