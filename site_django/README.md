# Caderno de Idiomas — Django

Sistema único em Python (Django): páginas, login, banco de dados e painel
de administração no mesmo processo. Sem front separado, sem serviço
terceiro pra autenticação.

## O que tem hoje

- **Contas de verdade**: cadastro com e-mail + senha (hash seguro do
  próprio Django), login, logout, recuperação de senha por e-mail e
  troca de senha estando logado.
- **Progresso no banco**: cada palavra marcada "sabia"/"errei" é salva em
  `Progress`, ligada ao usuário — funciona em qualquer aparelho que você
  faça login, não fica preso a um navegador.
- **Painel de administração** em `/admin/` — gerencie tópicos, palavras
  (com exportação pra CSV) e veja o progresso de qualquer usuário sem
  escrever código.
- **Dashboard**: anel de progresso geral, sequência de dias estudados
  (streak), banner "continuar de onde parou", busca e filtros por tópico.
- **Estudo**: palavra em português ou foto real (buscada ao vivo na
  Wikipedia). A opção "Foto" só aparece quando o tópico tem pelo menos
  uma palavra com `has_photo=True` — sem emoji em lugar nenhum. O campo
  de digitação da tradução fica sempre visível (não é um modo opcional),
  com correção tolerante a acento e pequenos erros. Erros da rodada
  podem ser revisados na hora, sem sair do tópico. Filtro "só o que
  ainda não sei" por tópico.

## Estrutura

```
site_django/
  manage.py
  idiomas_site/        configurações do projeto (settings, urls)
  flashcards/           o app: models, views, templates, admin
    models.py            Topic, Word (com has_photo), Progress, Profile (streak)
    views.py             páginas + endpoints de API (progresso, imagem)
    forms.py             cadastro (email como login)
    admin.py             painel de administração + exportação CSV
    templates/flashcards/
    static/flashcards/
    management/commands/
      import_words.py    importa tópicos/palavras (JSON ou CSV)
      check_photos.py    verifica na Wikipedia se cada palavra tem foto
                          e atualiza has_photo sozinho
```

A pasta `app/` na raiz (FastAPI + front separado) foi o rascunho anterior
— pode ser apagada quando quiser, este projeto não depende dela (só reusa
`app/data/words.json` como fonte pra popular o banco pela primeira vez).

## Rodando localmente

```bash
cd site_django
python -m venv .venv
.venv/Scripts/activate          # Windows; Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py import_words        # popula tópicos/palavras (só roda se o banco estiver vazio)
python manage.py createsuperuser     # sua conta de admin
python manage.py runserver
```

Acesse `http://localhost:8000`. O painel de administração fica em
`http://localhost:8000/admin/`.

Pra rodar os testes automatizados (autenticação, controle de acesso,
progresso, sequência de dias):

```bash
python manage.py test flashcards
```

## Gerenciando o vocabulário

`import_words` não sobrescreve nada se já houver palavras no banco —
protege edições feitas no admin. Pra forçar recarregar tudo, use
`python manage.py import_words --force` (isso apaga edições manuais).

Aceita tanto JSON quanto CSV via `--file`:

```bash
python manage.py import_words --file caminho/vocabulario_novo.json
python manage.py import_words --file caminho/vocabulario_novo.csv
```

O CSV precisa das colunas `topic_id,topic_name,topic_emoji,pt,en,has_photo`
(veja `prompts/gerar-vocabulario.md` pra gerar um vocabulário novo com
uma IA, já nesse formato). O admin também exporta as palavras existentes
pra CSV (selecione linhas em `/admin/flashcards/word/` → ação
"Exportar selecionadas para CSV").

Pra reconferir na Wikipedia, palavra por palavra, se `has_photo` está
certo (em vez de confiar só no que foi importado):

```bash
python manage.py check_photos
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
   `DJANGO_ALLOWED_HOSTS=seuapp.onrender.com`. Nunca commite um `.env`
   de verdade — o `.gitignore` já bloqueia isso, e todas as chaves ficam
   só em variável de ambiente.
5. Depois do primeiro deploy, rode uma vez (console do serviço):
   ```bash
   python manage.py migrate
   python manage.py import_words
   python manage.py createsuperuser
   ```

Estático (CSS/JS) já é servido pelo próprio Django via WhiteNoise — não
precisa de Vercel/Netlify nem de configurar nada à parte.

## Próximos passos possíveis

Veja `prompts/melhorar-sistema.md` — é um prompt pronto pra pedir pra
uma IA analisar o estado atual e priorizar as próximas melhorias
(repetição espaçada de verdade, dificuldade adaptativa, etc.).

- **Espanhol/Francês** — o seletor de idioma já existe na UI; falta
  adicionar as traduções no `Word` (hoje só há `en`) e um campo pra
  escolher o idioma alvo por usuário.
- **Vender depois** — dá pra adicionar um campo `plan` no `Profile` e
  checar nas views antes de liberar tópicos "premium"; o Django admin já
  serve pra gerenciar isso manualmente antes de automatizar cobrança.
