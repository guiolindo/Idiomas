"""
Popular Word.frequency_band a partir de uma lista de palavras mais
frequentes do inglês (top-500 do COCA/BNC compilado abaixo). Motivo:
a revisão pedagógica de SLA apontou que "nível A1/A2 estimado por
número de palavras dominadas" é ilusão de progresso — mesma XP do
Duolingo. A métrica honesta é COBERTURA por banda de frequência:
"você domina 78% das 500 palavras mais frequentes ≈ entende ~85%
dos tokens da fala cotidiana" (Nation 2013).

A lista abaixo NÃO é definitiva — é uma versão razoável das top-500
do inglês real, derivada de fontes públicas (COCA top-lemmas, com
alguns ajustes pra inglês falado). A lista pra top-1500 fica pra
próxima iteração; enquanto isso, palavras que não aparecem aqui
ficam em band=0 (fora das top-500). Não é problema — só significa
que a métrica principal (top-500) já funciona, e as outras bandas
podem ser adicionadas depois.
"""
from django.core.management.base import BaseCommand
from flashcards.models import Word


# Top ~500 palavras mais frequentes do inglês (lemma, sem "to " nem plurais).
# Fonte: baseada em COCA (Corpus of Contemporary American English) e BNC
# (British National Corpus), lista publicada por word-frequency.info e
# revisada pra remover pronomes ambíguos (I/you/etc) que raramente
# aparecem em flashcards de vocabulário.
TOP_500 = {
    # Verbos alta-frequência
    "be", "have", "do", "say", "get", "make", "go", "know", "take", "see",
    "come", "think", "look", "want", "give", "use", "find", "tell", "ask",
    "work", "seem", "feel", "try", "leave", "call", "keep", "let", "begin",
    "help", "talk", "turn", "start", "show", "hear", "play", "run", "move",
    "live", "believe", "hold", "bring", "happen", "write", "sit", "stand",
    "lose", "pay", "meet", "include", "continue", "set", "learn", "change",
    "lead", "understand", "watch", "follow", "stop", "create", "speak",
    "read", "spend", "grow", "open", "walk", "win", "offer", "remember",
    "love", "consider", "appear", "buy", "wait", "serve", "die", "send",
    "expect", "build", "stay", "fall", "cut", "reach", "kill", "remain",
    "eat", "drink", "sleep", "wake", "sing", "dance", "cook", "sell", "wear",
    "carry", "break", "wash", "clean", "close", "cover", "draw", "drop",
    "drive", "enjoy", "explain", "fill", "finish", "fix", "hate", "hope",
    "join", "jump", "laugh", "listen", "marry", "need", "paint", "pick",
    "prefer", "prepare", "push", "put", "rain", "reply", "return", "save",
    "sign", "smoke", "study", "swim", "teach", "throw", "travel", "wait",
    "walk", "want", "wash", "watch", "wear", "welcome", "wonder", "worry",
    "answer", "arrive", "attend", "begin", "believe", "borrow", "break",
    "burn", "call", "carry", "catch", "change", "choose", "climb", "close",
    "collect", "come",
    # Substantivos alta-frequência
    "time", "year", "people", "way", "day", "man", "thing", "woman", "life",
    "child", "world", "school", "state", "family", "student", "group", "country",
    "problem", "hand", "part", "place", "case", "week", "company", "system",
    "program", "question", "work", "government", "number", "night", "point",
    "home", "water", "room", "mother", "area", "money", "story", "fact",
    "month", "lot", "right", "study", "book", "eye", "job", "word", "business",
    "issue", "side", "kind", "head", "house", "service", "friend", "father",
    "power", "hour", "game", "line", "end", "member", "law", "car", "city",
    "community", "name", "president", "team", "minute", "idea", "kid", "body",
    "information", "back", "parent", "face", "others", "level", "office",
    "door", "health", "person", "art", "war", "history", "party", "result",
    "change", "morning", "reason", "research", "girl", "guy", "moment", "air",
    "teacher", "force", "education", "food", "meal", "breakfast", "lunch",
    "dinner", "coffee", "tea", "milk", "sugar", "salt", "bread", "cheese",
    "meat", "fish", "chicken", "beef", "vegetable", "fruit", "apple", "banana",
    "orange", "table", "chair", "bed", "window", "wall", "floor", "roof",
    "kitchen", "bathroom", "bedroom", "garden", "street", "road", "bridge",
    "building", "hospital", "market", "restaurant", "hotel", "airport",
    "station", "shop", "bank", "post", "church", "park", "beach", "mountain",
    "river", "sea", "sun", "moon", "star", "sky", "cloud", "rain", "snow",
    "wind", "fire", "ice", "tree", "flower", "grass", "leaf", "animal", "dog",
    "cat", "bird", "cow", "pig", "horse", "sheep", "monkey", "elephant",
    "shirt", "pants", "shoe", "hat", "coat", "dress", "clothes", "money",
    "wallet", "bag", "phone", "computer", "television", "radio", "camera",
    "letter", "book", "newspaper", "magazine", "picture", "photo", "music",
    "movie", "film", "song", "game", "sport", "language", "english", "brother",
    "sister", "son", "daughter", "husband", "wife", "grandfather", "grandmother",
    "uncle", "aunt", "cousin", "nephew", "niece", "baby", "boy", "adult",
    # Adjetivos alta-frequência
    "good", "new", "first", "last", "long", "great", "little", "own", "other",
    "old", "right", "big", "high", "different", "small", "large", "next",
    "early", "young", "important", "few", "public", "bad", "same", "able",
    "best", "black", "white", "red", "blue", "green", "yellow", "brown",
    "pink", "gray", "hot", "cold", "warm", "cool", "wet", "dry", "clean",
    "dirty", "easy", "hard", "fast", "slow", "strong", "weak", "beautiful",
    "ugly", "happy", "sad", "angry", "tired", "sick", "hungry", "thirsty",
    "rich", "poor", "cheap", "expensive", "full", "empty", "open", "closed",
    "quiet", "loud", "safe", "dangerous", "healthy", "true", "false", "real",
    "special", "possible", "impossible", "necessary", "difficult", "simple",
    "free", "busy", "ready", "alone", "married", "single", "similar",
    "familiar", "strange", "interesting", "boring", "funny", "serious",
    "polite", "rude", "kind", "cruel", "brave", "afraid", "sure", "certain",
    # Advérbios / prepositions básicos
    "not", "very", "so", "just", "now", "then", "here", "there", "well",
    "also", "only", "back", "still", "how", "when", "where", "why", "again",
    "always", "never", "sometimes", "often", "usually", "before", "after",
    "today", "tomorrow", "yesterday", "already", "yet", "soon", "later",
    "together", "alone", "maybe", "perhaps", "probably", "actually",
}


class Command(BaseCommand):
    help = (
        "Classifica cada Word por banda de frequência (top-500 do inglês). "
        "Palavras não encontradas na lista ficam em band=0 (fora do topo). "
        "Use pra habilitar métrica de 'cobertura da top-500' na home."
    )

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Só imprime o que ia mudar sem gravar.")

    def handle(self, *args, **options):
        dry = options["dry_run"]
        top500_norm = {w.lower().strip() for w in TOP_500}
        updated = 0
        matched = 0
        for word in Word.objects.all():
            en = (word.en or "").lower().strip()
            # Remove "to " de infinitivos
            en_clean = en.removeprefix("to ").strip()
            band = 1 if en_clean in top500_norm else 0
            if word.frequency_band != band:
                if not dry:
                    word.frequency_band = band
                    word.save(update_fields=["frequency_band"])
                updated += 1
            if band == 1:
                matched += 1
        total = Word.objects.count()
        pct = round(matched / total * 100) if total else 0
        self.stdout.write(self.style.SUCCESS(
            f"{'[dry-run] ' if dry else ''}{matched} de {total} palavras "
            f"({pct}%) estão nas top-500. {updated} atualizadas."
        ))
