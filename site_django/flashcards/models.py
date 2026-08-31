from django.conf import settings
from django.db import models


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

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.pt} → {self.en}"


class Progress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="progress")
    word = models.ForeignKey(Word, on_delete=models.CASCADE, related_name="progress")
    known = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "word")
        verbose_name_plural = "progress"

    def __str__(self):
        return f"{self.user} · {self.word} · {'sabia' if self.known else 'errou'}"


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    streak_count = models.PositiveIntegerField(default=0)
    last_study_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Perfil de {self.user}"
