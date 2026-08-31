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
            "--file", default=None,
            help="Caminho pra um arquivo alternativo (.json ou .csv — ex: um "
                 "vocabulário maior gerado por IA). Por padrão usa app/data/words.json.",
        )

    def handle(self, *args, **options):
        if Word.objects.exists() and not options["force"]:
            self.stdout.write(self.style.WARNING(
                "Já existem palavras no banco. Rodar este comando de novo apagaria "
                "qualquer edição feita no admin. Use --force se é isso mesmo que você quer."
            ))
            return

        path = Path(options["file"]) if options["file"] else DATA_PATH
        if path.suffix.lower() == ".csv":
            topics = load_topics_from_csv(path)
        elif path.suffix.lower() == ".json":
            topics = load_topics_from_json(path)
        else:
            raise CommandError(f"Formato não reconhecido: {path.suffix} (use .json ou .csv)")

        for order, topic_data in enumerate(topics):
            topic, created = Topic.objects.update_or_create(
                slug=slugify(topic_data["id"]),
                defaults={"name": topic_data["name"], "emoji": topic_data["emoji"], "order": order},
            )
            topic.words.all().delete()
            Word.objects.bulk_create([
                Word(topic=topic, pt=w["pt"], en=w["en"], has_photo=w["has_photo"], order=i)
                for i, w in enumerate(topic_data["words"])
            ])
            action = "criado" if created else "atualizado"
            self.stdout.write(f"{action}: {topic.name} ({len(topic_data['words'])} palavras)")

        self.stdout.write(self.style.SUCCESS(
            f"Importação concluída: {Topic.objects.count()} tópicos, {Word.objects.count()} palavras."
        ))
