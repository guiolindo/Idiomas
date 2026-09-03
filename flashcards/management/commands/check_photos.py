import time

from django.core.management.base import BaseCommand

from flashcards.models import Word
from flashcards.photos import GEMINI_API_KEY, PEXELS_ENABLED, fetch_and_validate_photo, fetch_photo


class Command(BaseCommand):
    help = (
        "Popula Word.photo_url/photo_variants pra cada palavra, validando cada "
        "candidato com Gemini Vision antes de aceitar (padrão, com GEMINI_API_KEY "
        "configurada) — é a forma que escala pra milhares de palavras, em vez de "
        "curar exceção por exceção no código. Sem GEMINI_API_KEY, cai pro "
        "ranking por alt-text (mais rápido, menos confiável). Rate limit Pexels "
        "free: 200/hora — em lotes grandes use --sleep maior."
    )

    def add_arguments(self, parser):
        parser.add_argument("--topic", default=None, help="Rodar só num tópico (slug).")
        parser.add_argument("--limit", type=int, default=0, help="Máximo de palavras (0 = todas).")
        parser.add_argument("--only-missing", action="store_true",
                            help="Pular palavras que já têm photo_url salva.")
        parser.add_argument("--sleep", type=float, default=1.5,
                            help="Segundos entre palavras (default 1.5). Com Vision ligado, "
                                 "cada palavra já leva ~2-6s por causa das chamadas de imagem.")
        parser.add_argument("--no-vision", action="store_true",
                            help="Desliga a validação com Gemini Vision (mais rápido e sem "
                                 "gastar quota, mas volta a confiar só no texto alternativo — "
                                 "sujeito aos mesmos erros de sempre).")

    def handle(self, *args, **options):
        if not PEXELS_ENABLED:
            self.stdout.write(self.style.WARNING(
                "PEXELS_API_KEY não configurada — usando só o fallback da Wikipedia."
            ))
        use_vision = bool(GEMINI_API_KEY) and not options["no_vision"]
        if not use_vision:
            self.stdout.write(self.style.WARNING(
                "Rodando SEM validação visual (GEMINI_API_KEY ausente ou --no-vision). "
                "Fotos vão confiar só no texto alternativo do Pexels — mais rápido, "
                "mais sujeito a erro de sentido ambíguo."
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
        self.stdout.write(f"Vou checar {total} palavras{' (com Vision)' if use_vision else ''}.")
        changed = 0
        rejected_by_vision = 0

        for i, word in enumerate(words, start=1):
            en = word.en.removeprefix("to ")
            result = fetch_and_validate_photo(en) if use_vision else fetch_photo(en)

            has_photo = result.get("found", False)
            url = result.get("url", "") if has_photo else ""
            page = result.get("page", "") if has_photo else ""
            credit = result.get("credit", "") if has_photo else ""
            variants = result.get("variants", []) if has_photo else []
            source = result.get("source", "-") if has_photo else "sem foto"
            vision_note = ""
            if result.get("vision_checked"):
                if has_photo:
                    vision_note = " [vision ok]"
                else:
                    rejected_by_vision += 1
                    vision_note = f" [vision rejeitou: {result.get('vision_reason', '')[:50]}]"

            fields = (word.has_photo, word.photo_url, word.photo_page,
                      word.photo_credit, word.photo_variants)
            if fields != (has_photo, url, page, credit, variants):
                word.has_photo = has_photo
                word.photo_url = url
                word.photo_page = page
                word.photo_credit = credit
                word.photo_variants = variants
                word.save(update_fields=["has_photo", "photo_url", "photo_page",
                                          "photo_credit", "photo_variants"])
                changed += 1
            self.stdout.write(f"[{i}/{total}] {word.pt} ({en}): {source}{vision_note}")
            if i < total:
                time.sleep(options["sleep"])

        msg = f"Concluído. {changed} palavras atualizadas."
        if use_vision:
            msg += f" {rejected_by_vision} rejeitadas pelo Vision (ficaram sem foto em vez de errada)."
        self.stdout.write(self.style.SUCCESS(msg))
