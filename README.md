# Caderno de Idiomas

Flashcards de vocabulário português → inglês, com conta de usuário,
progresso salvo no banco e painel de administração.

## Onde está o quê

- **`site_django/`** — o sistema atual. Django único (páginas, login,
  banco, admin), sem front separado. Veja `site_django/README.md` pra
  rodar localmente e fazer deploy.
- **`app/`** — protótipo anterior (FastAPI + front estático + Supabase),
  mantido só de referência. Não é mais usado.
- **`idiomas.html`** — o primeiro rascunho, um único arquivo HTML/JS
  (sem backend). Histórico do projeto.
- **`extract_data.py`** — script usado uma vez pra extrair o vocabulário
  do `idiomas.html` em JSON (`app/data/words.json`), fonte que o Django
  importa via `manage.py import_words`.

## Começando

```bash
cd site_django
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py import_words
python manage.py createsuperuser
python manage.py runserver
```
