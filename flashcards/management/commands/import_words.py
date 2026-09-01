import csv
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from flashcards.models import Topic, Word

DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "words.json"


def _truthy(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("sim", "true", "1", "yes", "y")


def load_topics_from_json(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    topics = []
    for topic_data in data["topics"]:
        topics.append({
            "id": topic_data["id"],
            "name": topic_data["name"],
            "emoji": topic_data.get("emoji", "🔤"),
            "words": [
                {"pt": w["pt"], "en": w["en"], "has_photo": _truthy(w.get("has_photo", True))}
                for w in topic_data["words"]
            ],
        })
    return topics


def load_topics_from_csv(path: Path) -> list[dict]:
    """Espera as colunas: topic_id, topic_name, topic_emoji, pt, en, has_photo"""
    by_id = {}
    order = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            tid = row["topic_id"].strip()
            if tid not in by_id:
                by_id[tid] = {
                    "id": tid,
                    "name": row.get("topic_name", tid).strip(),
                    "emoji": row.get("topic_emoji", "🔤").strip() or "🔤",
                    "words": [],
                }
                order.append(tid)
            by_id[tid]["words"].append({
                "pt": row["pt"].strip(),
                "en": row["en"].strip(),
                "has_photo": _truthy(row.get("has_photo", "sim")),
            })
    return [by_id[tid] for tid in order]


class Command(BaseCommand):
    help = "Importa topicos e palavras (JSON ou CSV) para o banco (só na primeira vez, a menos que --force seja usado)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force", action="store_true",
            help="Apaga e recria as palavras de cada tópico mesmo que já existam "
                 "(CUIDADO: destrói edições feitas manualmente no admin).",
        )
        parser.add_argument(
            "--merge", action="store_true",
            help="Só adiciona tópicos e palavras novas — não toca no que já "
                 "existe (preserva progresso do aluno). Ideal pra ampliar o "
                 "vocabulário sem quebrar nada.",
        )
        parser.add_argument(
            "--file", default=None,
            help="Caminho pra um arquivo alternativo (.json ou .csv — ex: um "
                 "vocabulário maior gerado por IA). Por padrão usa app/data/words.json.",
        )

    def handle(self, *args, **options):
        if Word.objects.exists() and not options["force"] and not options["merge"]:
            self.stdout.write(self.style.WARNING(
                "Já existem palavras no banco. Rodar este comando de novo apagaria "
                "qualquer edição feita no admin. Use --force pra substituir tudo, ou "
                "--merge pra só adicionar tópicos/palavras novas sem tocar no existente."
            ))
            return

        path = Path(options["file"]) if options["file"] else DATA_PATH
        if path.suffix.lower() == ".csv":
            topics = load_topics_from_csv(path)
        elif path.suffix.lower() == ".json":
            topics = load_topics_from_json(path)
        else:
            raise CommandError(f"Formato não reconhecido: {path.suffix} (use .json ou .csv)")

        merge = options["merge"]
        existing_last_order = Topic.objects.count() if merge else 0
        added_topics = 0
        added_words = 0
        for order, topic_data in enumerate(topics):
            slug = slugify(topic_data["id"])
            if merge:
                topic, created = Topic.objects.get_or_create(
                    slug=slug,
                    defaults={
                        "name": topic_data["name"],
                        "emoji": topic_data["emoji"],
                        "order": existing_last_order + order,
                    },
                )
                existing_en = set(topic.words.values_list("en", flat=True))
                start_i = topic.words.count()
                new_words = [w for w in topic_data["words"] if w["en"] not in existing_en]
                Word.objects.bulk_create([
                    Word(topic=topic, pt=w["pt"], en=w["en"], has_photo=w["has_photo"],
                         order=start_i + i)
                    for i, w in enumerate(new_words)
                ])
                added_words += len(new_words)
                added_topics += 1 if created else 0
                self.stdout.write(f"{'+' if created else '='} {topic.name}: {len(new_words)} palavras novas")
                continue
            topic, created = Topic.objects.update_or_create(
                slug=slug,
                defaults={"name": topic_data["name"], "emoji": topic_data["emoji"], "order": order},
            )
            topic.words.all().delete()
            Word.objects.bulk_create([
                Word(topic=topic, pt=w["pt"], en=w["en"], has_photo=w["has_photo"], order=i)
                for i, w in enumerate(topic_data["words"])
            ])
            action = "criado" if created else "atualizado"
            self.stdout.write(f"{action}: {topic.name} ({len(topic_data['words'])} palavras)")

        if merge:
            self.stdout.write(self.style.SUCCESS(
                f"Merge concluído: {added_topics} tópicos novos, {added_words} palavras novas. "
                f"Total agora: {Topic.objects.count()} tópicos, {Word.objects.count()} palavras."
            ))
            return

        self.stdout.write(self.style.SUCCESS(
            f"Importação concluída: {Topic.objects.count()} tópicos, {Word.objects.count()} palavras."
        ))
