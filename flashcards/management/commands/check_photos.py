import time

from django.core.management.base import BaseCommand

from flashcards.models import Word
from flashcards.photos import PEXELS_ENABLED, fetch_photo


class Command(BaseCommand):
    help = (
        "Verifica, palavra por palavra (Pexels primeiro, Wikipedia de "
        "fallback), se existe uma foto que faça sentido, e atualiza "
        "Word.has_photo/photo_url/photo_page/photo_credit. A URL fica salva, "
        "então o cartão de estudo não precisa buscar ao vivo depois. Pra "
        "não estourar a cota do Pexels (200/hora no plano free), use "
        "--sleep=20 quando rodar em lote grande, ou --topic=slug pra rodar "
        "só num tópico por vez."
    )

    def add_arguments(self, parser):
        parser.add_argument("--topic", default=None, help="Rodar só num tópico (slug).")
        parser.add_argument("--limit", type=int, default=0, help="Máximo de palavras a checar (0 = todas).")
        parser.add_argument("--only-missing", action="store_true",
                            help="Pular palavras que já têm photo_url salva.")
        parser.add_argument("--sleep", type=float, default=1.5,
                            help="Segundos entre chamadas (default 1.5 — subir pra 20 se rodar >200 palavras).")

    def handle(self, *args, **options):
        if not PEXELS_ENABLED:
            self.stdout.write(self.style.WARNING(
                "PEXELS_API_KEY não configurada — usando só o fallback da Wikipedia."
            ))
        qs = Word.objects.all().order_by("topic__order", "order")
        if options["topic"]:
            qs = qs.filter(topic__slug=options["topic"])
        if options["only_missing"]:
            qs = qs.filter(photo_url="")
        if options["limit"]:
            qs = qs[:options["limit"]]
        words = list(qs)
        total = len(words)
        self.stdout.write(f"Vou checar {total} palavras.")
        changed = 0
        for i, word in enumerate(words, start=1):
            result = fetch_photo(word.en.removeprefix("to "))
            has_photo = result["found"]
            url = result.get("url", "") if has_photo else ""
            page = result.get("page", "") if has_photo else ""
            credit = result.get("credit", "") if has_photo else ""
            fields = (word.has_photo, word.photo_url, word.photo_page, word.photo_credit)
            if fields != (has_photo, url, page, credit):
                word.has_photo = has_photo
                word.photo_url = url
                word.photo_page = page
                word.photo_credit = credit
                word.save(update_fields=["has_photo", "photo_url", "photo_page", "photo_credit"])
                changed += 1
            source = result.get("source", "-")
            self.stdout.write(f"[{i}/{total}] {word.pt} ({word.en}): {source if has_photo else 'sem foto'}")
            if i < total:
                time.sleep(options["sleep"])

        self.stdout.write(self.style.SUCCESS(f"Concluído. {changed} palavras atualizadas."))
