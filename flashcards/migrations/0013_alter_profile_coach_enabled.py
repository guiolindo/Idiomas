# Ligar o coach de IA por padrão pra todos.
# A cobertura legal fica na aceitação dos Termos/Privacidade — que foram
# atualizados junto com esta migração pra deixar explícito que ao criar
# conta o usuário está ciente do coach. Quem não quiser continua podendo
# desligar em Configurações a qualquer momento.
from django.db import migrations, models


def enable_coach_for_existing_profiles(apps, schema_editor):
    Profile = apps.get_model("flashcards", "Profile")
    Profile.objects.filter(coach_enabled=False).update(coach_enabled=True)


def disable_coach_for_existing_profiles(apps, schema_editor):
    # Reverse: volta todo mundo pra desligado (estado privacy-by-default original)
    Profile = apps.get_model("flashcards", "Profile")
    Profile.objects.update(coach_enabled=False)


class Migration(migrations.Migration):

    dependencies = [
        ('flashcards', '0012_profile_coach_enabled'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='coach_enabled',
            field=models.BooleanField(default=True, help_text='Se ligado, envia resumo de erros/rodadas pra Gemini/Groq gerar feedback. Padrão ligado — cobertura pela aceitação dos Termos/Privacidade na criação da conta.', verbose_name='coach de IA ligado'),
        ),
        migrations.RunPython(enable_coach_for_existing_profiles, disable_coach_for_existing_profiles),
    ]
