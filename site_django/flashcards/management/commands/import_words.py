import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from flashcards.models import Topic, Word

DATA_PATH = Path(__file__).resolve().parents[4] / "app" / "data" / "words.json"


class Command(BaseCommand):
    help = "Importa topicos e palavras de app/data/words.json para o banco (só na primeira vez, a menos que --force seja usado)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force", action="store_true",
            help="Apaga e recria as palavras de cada tópico mesmo que já existam "
                 "(CUIDADO: destrói edições feitas manualmente no admin).",
        )
        parser.add_argument(
            "--file", default=None,
            help="Caminho pra um words.json alternativo (ex: um vocabulário maior "
                 "gerado por IA). Por padrão usa app/data/words.json.",
        )

    def handle(self, *args, **options):
        if Word.objects.exists() and not options["force"]:
            self.stdout.write(self.style.WARNING(
                "Já existem palavras no banco. Rodar este comando de novo apagaria "
                "qualquer edição feita no admin. Use --force se é isso mesmo que você quer."
            ))
            return

        path = Path(options["file"]) if options["file"] else DATA_PATH
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        for order, topic_data in enumerate(data["topics"]):
            topic, created = Topic.objects.update_or_create(
                slug=slugify(topic_data["id"]),
                defaults={"name": topic_data["name"], "emoji": topic_data.get("emoji", "🔤"), "order": order},
            )
            topic.words.all().delete()
            Word.objects.bulk_create([
                Word(topic=topic, pt=w["pt"], en=w["en"], order=i)
                for i, w in enumerate(topic_data["words"])
            ])
            action = "criado" if created else "atualizado"
            self.stdout.write(f"{action}: {topic.name} ({len(topic_data['words'])} palavras)")

        self.stdout.write(self.style.SUCCESS(
            f"Importação concluída: {Topic.objects.count()} tópicos, {Word.objects.count()} palavras."
        ))
