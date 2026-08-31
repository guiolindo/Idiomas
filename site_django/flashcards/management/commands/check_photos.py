import time

import httpx
from django.core.management.base import BaseCommand

from flashcards.models import Word

HEADERS = {
    "User-Agent": "CadernoDeIdiomas/1.0 (app pessoal de flashcards; contato: brzueira342386@gmail.com)"
}


def word_has_photo(en: str) -> bool:
    title = en.replace(" ", "_")
    try:
        resp = httpx.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}",
            headers=HEADERS, timeout=8, follow_redirects=True,
        )
    except httpx.HTTPError:
        return False
    if resp.status_code != 200:
        return False
    data = resp.json()
    return bool(data.get("thumbnail")) and data.get("type") != "disambiguation"


class Command(BaseCommand):
    help = (
        "Verifica na Wikipedia, palavra por palavra, se existe uma foto que faça "
        "sentido, e atualiza Word.has_photo de acordo (em vez de adivinhar)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--all", action="store_true",
            help="Reverifica todas as palavras (por padrão só verifica as que "
                 "ainda não foram checadas nesta sessão de import).",
        )

    def handle(self, *args, **options):
        words = Word.objects.all().order_by("topic__order", "order")
        total = words.count()
        changed = 0
        for i, word in enumerate(words, start=1):
            has_photo = word_has_photo(word.en.removeprefix("to "))
            if word.has_photo != has_photo:
                word.has_photo = has_photo
                word.save(update_fields=["has_photo"])
                changed += 1
            self.stdout.write(f"[{i}/{total}] {word.pt} ({word.en}): {'foto' if has_photo else 'sem foto'}")
            time.sleep(0.15)  # educado com a API da Wikipedia

        self.stdout.write(self.style.SUCCESS(f"Concluído. {changed} palavras atualizadas."))
