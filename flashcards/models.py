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
    photo_url = models.URLField("foto (capa)", max_length=500, blank=True, default="")
    photo_page = models.URLField("página de origem da foto", max_length=500, blank=True, default="")
    photo_credit = models.CharField("crédito da foto", max_length=120, blank=True, default="")
    # Alternativas de foto pra evitar mostrar sempre a mesma imagem. Formato:
    # [{"url": "...", "page": "...", "credit": "..."}, ...]
    photo_variants = models.JSONField("outras fotos disponíveis", default=list, blank=True)
    # Banda de frequência da palavra no inglês real (COCA/BNC):
    #   1 = top 500 (95% de cobertura de fala informal)
    #   2 = top 501-1500 (~85% cobertura escrita)
    #   3 = top 1501-3000 (~90% cobertura escrita)
    #   0 = fora das 3000 mais frequentes (vocabulário especializado)
    # A ideia é substituir "nível A1 por número de palavras dominadas"
    # (que a revisão de SLA chamou de "ilusão de progresso — mesma XP do
    # Duolingo") por métrica honesta: "78% das top-500". Popular via
    # management command com a lista de referência.
    frequency_band = models.PositiveSmallIntegerField(
        "banda de frequência", default=0, db_index=True,
        help_text="1=top-500, 2=top-1500, 3=top-3000, 0=fora"
    )

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
    # Idioma em que a última resposta errada foi escrita — 'en' (modos
    # Escrita/Voz, alvo em inglês) ou 'pt' (modos Ditado/Interpretação,
    # alvo em português). Sem esse campo, a dica "última vez você
    # escreveu X" vazava entre modos: quem errou "people" em Escrita
    # via a mesma dica ao tentar traduzir de volta pra "pessoa" em
    # Ditado — sem sentido.
    last_wrong_lang = models.CharField(max_length=2, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)
    # Leech: palavra que o aluno erra várias vezes seguidas — merece atenção
    # extra (aviso visual no cartão + o coach de IA fica sabendo pra
    # comentar sobre ela). Contador zera em qualquer acerto ("Quase" ou
    # "Sabia"); marca é limpa só num acerto confiante ("Sabia").
    consecutive_errors = models.PositiveSmallIntegerField(default=0)
    is_leech = models.BooleanField(default=False, db_index=True)

    class Meta:
        unique_together = ("user", "word")
        verbose_name_plural = "progress"

    def __str__(self):
        return f"{self.user} · {self.word} · nível {self.level}"

    @property
    def mastered(self):
        return self.level >= SRS_MAX_LEVEL

    # Limiar pra considerar uma palavra "travada" (leech). 3 erros seguidos
    # é forte o suficiente pra não marcar por deslize, e leve o suficiente
    # pra o aviso aparecer antes do aluno desistir da palavra.
    LEECH_THRESHOLD = 3

    def apply_feedback(self, result: str, wrong_answer: str = "", answer_lang: str = "en"):
        """result: 'miss' | 'soso' | 'know'.
        answer_lang: 'en' ou 'pt' — em qual idioma a resposta foi dada.
        Guardado junto pra "última vez você escreveu X" só reaparecer no
        MESMO modo onde foi errada."""
        now = timezone.now()
        if result == "miss":
            self.level = 0
            self.next_review = now + timezone.timedelta(days=SRS_INTERVALS_DAYS[0])
            self.last_wrong_answer = wrong_answer[:100]
            self.last_wrong_lang = answer_lang if answer_lang in ("en", "pt") else ""
            self.consecutive_errors += 1
            if self.consecutive_errors >= self.LEECH_THRESHOLD:
                self.is_leech = True
        elif result == "soso":
            self.next_review = now + timezone.timedelta(days=1)
            self.last_wrong_answer = ""
            self.last_wrong_lang = ""
            self.consecutive_errors = 0
            # "Quase" zera o streak mas NÃO tira o rótulo de leech — o aluno
            # ainda não domina confiantemente. Só o "Sabia" limpa.
        else:  # know
            self.level = min(self.level + 1, SRS_MAX_LEVEL)
            self.next_review = now + timezone.timedelta(days=SRS_INTERVALS_DAYS[self.level])
            self.last_wrong_answer = ""
            self.last_wrong_lang = ""
            self.consecutive_errors = 0
            self.is_leech = False
        self.save()


class StudySession(models.Model):
    """Sessão de estudo autorizada pelo servidor.

    Sem isso (feedback da auditoria A-01), api_mark_progress aceitava qualquer
    word_id + modo enviados pelo cliente — dava pra corromper o próprio SRS
    marcando palavras arbitrárias como 'sabia' ou usar mode=challenge em
    qualquer request pra pular a gravação. Agora:

    - Ao abrir /estudar/, /misturar/ ou /desafio/, o servidor cria uma
      StudySession com os word_ids elegíveis e se afeta o SRS.
    - O id da sessão é passado pro cliente.
    - api_mark_progress rejeita:
        * session_id que não existe / expirou / não é do user
        * word_id que não está na lista da sessão
      A decisão de "afeta SRS" vem da sessão, não do cliente.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="study_sessions")
    mode = models.CharField(max_length=20)  # 'escrita' | 'ditado' | 'transcricao' | 'voz'
    word_ids = models.JSONField(default=list)  # lista de int com os ids elegíveis
    affects_srs = models.BooleanField(default=True)  # false pro modo Desafio
    topic_slug = models.CharField(max_length=40, blank=True, default="")  # opcional, só pra debug
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        indexes = [models.Index(fields=["user", "expires_at"])]

    def is_valid_now(self):
        return self.expires_at > timezone.now()

    def contains(self, word_id: int) -> bool:
        try:
            return int(word_id) in self.word_ids
        except (TypeError, ValueError):
            return False


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    streak_count = models.PositiveIntegerField(default=0)
    last_study_date = models.DateField(null=True, blank=True)

    # Coach com IA: última vez que o aluno respondeu algo, e o feedback
    # gerado a partir disso (gerado no máximo 1x por hora de atividade —
    # ver flashcards/ai_coach.py). Fica vazio/desligado sem GEMINI_API_KEY
    # ou GROQ_API_KEY configuradas.
    last_activity_at = models.DateTimeField(null=True, blank=True)
    ai_feedback = models.TextField(blank=True, default="")   # legado (frase única)
    ai_feedback_at = models.DateTimeField(null=True, blank=True)
    # Análise estruturada em 3 partes, gerada pelo prompt novo (strengths/
    # focus/recommendation). JSON: {"strengths":"","focus":"","recommendation":"","focus_topic":""}
    ai_analysis = models.JSONField(blank=True, default=dict)

    def __str__(self):
        return f"Perfil de {self.user}"
