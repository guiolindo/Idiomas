import time

from django.core.management.base import BaseCommand

from flashcards.models import Word
from flashcards.photos import PEXELS_ENABLED, fetch_photo


class Command(BaseCommand):
    help = (
        "Verifica, palavra por palavra (Pexels primeiro, Wikipedia de "
        "fallback), se existe uma foto que faça sentido, e atualiza "
        "Word.has_photo/photo_url/photo_page/photo_credit de acordo (em vez "
        "de adivinhar). A URL fica salva, então o cartão de estudo não "
        "precisa buscar ao vivo depois."
    )

    def handle(self, *args, **options):
        if not PEXELS_ENABLED:
            self.stdout.write(self.style.WARNING(
                "PEXELS_API_KEY não configurada — usando só o fallback da Wikipedia."
            ))
        words = Word.objects.all().order_by("topic__order", "order")
        total = words.count()
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
            self.stdout.write(f"[{i}/{total}] {word.pt} ({word.en}): {'foto' if has_photo else 'sem foto'}")
            time.sleep(0.15)  # educado com a API da Wikipedia

        self.stdout.write(self.style.SUCCESS(f"Concluído. {changed} palavras atualizadas."))
