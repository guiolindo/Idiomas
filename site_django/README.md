# Caderno de Idiomas — Django

Sistema único em Python (Django): páginas, login, banco de dados e painel
de administração no mesmo processo. Sem front separado, sem serviço
terceiro pra autenticação.

## O que tem hoje

- **Contas de verdade**: cadastro com e-mail + senha (hash seguro do
  próprio Django), sessão, logout.
- **Progresso no banco**: cada palavra marcada "sabia"/"errei" é salva em
  `Progress`, ligada ao usuário — funciona em qualquer aparelho que você
  faça login, não fica preso a um navegador.
- **Painel de administração** em `/admin/` — gerencie tópicos, palavras e
  veja o progresso de qualquer usuário sem escrever código.
- **Dashboard**: anel de progresso geral, sequência de dias estudados
  (streak), banner "continuar de onde parou", busca e filtros por tópico.
- **Estudo**: modo palavra/emoji/foto real (Wikimedia, buscada pelo
  próprio backend) e modo caderno (digita a resposta, checagem tolerante
  a acento/erro de digitação). Erros da rodada podem ser revisados na
  hora, sem sair do tópico.

## Estrutura

```
site_django/
  manage.py
  idiomas_site/        configurações do projeto (settings, urls)
  flashcards/           o app: models, views, templates, admin
    models.py            Topic, Word, Progress, Profile (streak)
    views.py             páginas + endpoints de API (progresso, imagem)
    forms.py             cadastro (email como login)
    admin.py             painel de administração
    templates/flashcards/
    static/flashcards/
    management/commands/import_words.py   importa app/data/words.json
```

A pasta `app/` na raiz (FastAPI + front separado) foi o rascunho anterior
— pode ser apagada quando quiser, este projeto não depende dela (só reusa
`app/data/words.json` como fonte pra popular o banco).

## Rodando localmente

```bash
cd site_django
python -m venv .venv
.venv/Scripts/activate          # Windows; Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py import_words        # popula tópicos/palavras a partir do words.json (só roda se o banco estiver vazio)
python manage.py createsuperuser     # sua conta de admin
python manage.py runserver
```

`import_words` não sobrescreve nada se já houver palavras no banco — protege
edições feitas no admin. Pra forçar recarregar tudo do `words.json`, use
`python manage.py import_words --force` (isso apaga edições manuais).

Acesse `http://localhost:8000`. O painel de administração fica em
`http://localhost:8000/admin/`.

Pra rodar os testes automatizados (autenticação, controle de acesso,
progresso, sequência de dias):

```bash
python manage.py test flashcards
```

## Deploy grátis (um único serviço)

[Render](https://render.com) ou [Railway](https://railway.app), plano free:

1. Suba este repositório no GitHub.
2. Crie um **Web Service** apontando pra pasta `site_django/`.
   - Build: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
   - Start: `gunicorn idiomas_site.wsgi --log-file -` (já está no `Procfile`)
3. Adicione um banco **PostgreSQL** free (Render/Railway/Neon) e cole a
   URL dele na variável de ambiente `DATABASE_URL`.
4. Defina as outras variáveis (veja `.env.example`): `DJANGO_SECRET_KEY`
   (gere uma nova, aleatória), `DJANGO_DEBUG=False`,
   `DJANGO_ALLOWED_HOSTS=seuapp.onrender.com`.
5. Depois do primeiro deploy, rode uma vez (console do serviço):
   ```bash
   python manage.py migrate
   python manage.py import_words
   python manage.py createsuperuser
   ```

Estático (CSS/JS) já é servido pelo próprio Django via WhiteNoise — não
precisa de Vercel/Netlify nem de configurar nada à parte.

## Próximos passos possíveis

- **Recuperação de senha** — Django já tem as views prontas
  (`PasswordResetView` etc.), só falta configurar envio de e-mail (hoje
  não está ligado).
- **Espanhol/Francês** — o seletor de idioma já existe na UI; falta
  adicionar as traduções no `Word` (hoje só há `en`) e um campo pra
  escolher o idioma alvo por usuário.
- **Vender depois** — dá pra adicionar um campo `plan` no `Profile` e
  checar nas views antes de liberar tópicos "premium"; o Django admin já
  serve pra gerenciar isso manualmente antes de automatizar cobrança.
