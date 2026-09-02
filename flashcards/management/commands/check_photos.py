import time

from django.core.management.base import BaseCommand

from flashcards.models import Word
from flashcards.photos import PEXELS_ENABLED, fetch_photo, validate_with_vision


class Command(BaseCommand):
    help = (
        "Popula Word.photo_url/photo_variants pra cada palavra. Ordem: Pexels "
        "com ranking por alt text (padrão) e Wikipedia como fallback. Use "
        "--strict pra validar cada foto com Gemini Vision antes de salvar "
        "(mais lento, gasta quota, mas rejeita fotos onde o assunto não é "
        "claramente o solicitado). Rate limit Pexels free: 200/hora — em "
        "lotes grandes use --sleep=20."
    )

    def add_arguments(self, parser):
        parser.add_argument("--topic", default=None, help="Rodar só num tópico (slug).")
        parser.add_argument("--limit", type=int, default=0, help="Máximo de palavras (0 = todas).")
        parser.add_argument("--only-missing", action="store_true",
                            help="Pular palavras que já têm photo_url salva.")
        parser.add_argument("--sleep", type=float, default=1.5,
                            help="Segundos entre chamadas (default 1.5).")
        parser.add_argument("--strict", action="store_true",
                            help="Valida cada foto candidata com Gemini Vision. Mais lento e "
                                 "gasta quota, mas rejeita fotos onde o assunto não é claro.")
        parser.add_argument("--min-score", type=int, default=6,
                            help="Score mínimo do Gemini pra aceitar (0-10, default 6). Só com --strict.")

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
        strict = options["strict"]
        min_score = options["min_score"]
        self.stdout.write(f"Vou checar {total} palavras{' (strict/vision)' if strict else ''}.")
        changed = 0
        rejected = 0
        for i, word in enumerate(words, start=1):
            result = fetch_photo(word.en.removeprefix("to "))
            has_photo = result.get("found", False)
            url = result.get("url", "") if has_photo else ""
            page = result.get("page", "") if has_photo else ""
            credit = result.get("credit", "") if has_photo else ""
            variants = result.get("variants", []) if has_photo else []
            score = result.get("top_score", 0) if has_photo else 0
            alt_hint = result.get("top_alt", "") if has_photo else ""
            source = result.get("source", "-") if has_photo else "sem foto"

            # Validação visual opcional
            vision_note = ""
            if has_photo and strict and url:
                v = validate_with_vision(url, word.en.removeprefix("to "))
                if v is None:
                    vision_note = " (vision indisponível)"
                elif not v["ok"] or v["score"] < min_score:
                    # Tenta próxima variante que passe
                    accepted = None
                    for var in variants[1:]:
                        vn = validate_with_vision(var["url"], word.en.removeprefix("to "))
                        if vn and vn["ok"] and vn["score"] >= min_score:
                            accepted = var
                            vision_note = f" (vision→variante {vn['score']}/10)"
                            break
                    if accepted:
                        url = accepted["url"]; page = accepted["page"]; credit = accepted["credit"]
                    else:
                        # nenhuma passou → rejeita a foto toda, mostra texto
                        has_photo = False
                        url = ""; page = ""; credit = ""; variants = []
                        vision_note = f" REJEITADA por vision ({v['reason'][:60]})"
                        rejected += 1
                else:
                    vision_note = f" (vision {v['score']}/10)"

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
            score_hint = f" [alt-score {score}]" if score else ""
            alt_snippet = f' "{alt_hint[:40]}"' if alt_hint else ""
            self.stdout.write(f"[{i}/{total}] {word.pt} ({word.en}): {source}{score_hint}{alt_snippet}{vision_note}")
            if i < total:
                time.sleep(options["sleep"])

        msg = f"Concluído. {changed} palavras atualizadas."
        if strict:
            msg += f" {rejected} rejeitadas pelo Gemini Vision."
        self.stdout.write(self.style.SUCCESS(msg))
