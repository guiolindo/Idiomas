import time

from django.core.management.base import BaseCommand

from flashcards.models import Word
from flashcards.wikipedia import fetch_summary


class Command(BaseCommand):
    help = (
        "Verifica na Wikipedia, palavra por palavra, se existe uma foto que faça "
        "sentido, e atualiza Word.has_photo/photo_url/photo_page de acordo (em "
        "vez de adivinhar). A URL fica salva, então o cartão de estudo não "
        "precisa buscar ao vivo depois."
    )

    def handle(self, *args, **options):
        words = Word.objects.all().order_by("topic__order", "order")
        total = words.count()
        changed = 0
        for i, word in enumerate(words, start=1):
            result = fetch_summary(word.en.removeprefix("to "))
            has_photo = result["found"]
            url = result.get("url", "") if has_photo else ""
            page = result.get("page", "") if has_photo else ""
            if (word.has_photo, word.photo_url, word.photo_page) != (has_photo, url, page):
                word.has_photo, word.photo_url, word.photo_page = has_photo, url, page
                word.save(update_fields=["has_photo", "photo_url", "photo_page"])
                changed += 1
            self.stdout.write(f"[{i}/{total}] {word.pt} ({word.en}): {'foto' if has_photo else 'sem foto'}")
            time.sleep(0.15)  # educado com a API da Wikipedia

        self.stdout.write(self.style.SUCCESS(f"Concluído. {changed} palavras atualizadas."))
