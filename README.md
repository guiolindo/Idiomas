# Caderno de Idiomas

Flashcards de vocabulário português → inglês. Sistema único em Python
(Django): páginas, login, banco de dados e painel de administração no
mesmo processo, na raiz deste repositório — sem front separado, sem
serviço terceiro pra autenticação.

## O que tem hoje

- **Contas de verdade**: cadastro com e-mail + senha (hash seguro do
  próprio Django), login, logout, recuperação de senha por e-mail e
  troca de senha estando logado.
- **Repetição espaçada (SRS leve)**: cada palavra tem um nível (0–4) e
  uma próxima revisão; a sessão de estudo só mostra o que está vencido
  ou nunca foi visto. Errei/Quase/Sabia com atalhos de teclado 1/2/3.
- **Painel de administração** em `/admin/` — gerencie tópicos, palavras
  (com exportação pra CSV) e veja o progresso de qualquer usuário sem
  escrever código.
- **Dashboard**: anel de progresso geral, sequência de dias estudados,
  widget de revisões vencidas, busca e filtros por tópico.
- **Estudo**: palavra em português ou foto real (cacheada do artigo da
  Wikipedia). A opção "Foto" só aparece quando o tópico tem pelo menos
  uma palavra fotografável — sem emoji em lugar nenhum.

## Estrutura

```
manage.py
idiomas_site/          configurações do projeto (settings, urls)
flashcards/             o app: models, views, templates, admin
  models.py              Topic, Word (has_photo, foto cacheada), Progress (SRS), Profile (streak)
  views.py               páginas + endpoints de API (progresso, imagem)
  wikipedia.py            busca de foto na Wikipedia (usado pela view e pelo check_photos)
  forms.py                cadastro (email como login)
  admin.py                painel de administração + exportação CSV
  templates/flashcards/
  static/flashcards/
  management/commands/
    import_words.py       importa tópicos/palavras (JSON ou CSV)
    check_photos.py       verifica na Wikipedia se cada palavra tem foto e atualiza sozinho
data/
  words.json              vocabulário base (33 tópicos, ~440 palavras)
prompts/                 prompts prontos pra pedir a uma IA que melhore o sistema ou gere mais vocabulário
```

## Rodando localmente

```bash
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

Testes automatizados:

```bash
python manage.py test flashcards
```

## Gerenciando o vocabulário

`import_words` não sobrescreve nada se já houver palavras no banco —
protege edições feitas no admin. Pra forçar recarregar tudo, use
`python manage.py import_words --force` (isso apaga edições manuais).

Aceita JSON ou CSV via `--file`:

```bash
python manage.py import_words --file caminho/vocabulario_novo.json
python manage.py import_words --file caminho/vocabulario_novo.csv
```

O CSV precisa das colunas `topic_id,topic_name,topic_emoji,pt,en,has_photo`
(veja `prompts/gerar-vocabulario.md` pra gerar vocabulário novo com uma
IA, já nesse formato). O admin também exporta as palavras existentes pra
CSV (selecione linhas em `/admin/flashcards/word/` → ação "Exportar
selecionadas para CSV").

Pra reconferir na Wikipedia, palavra por palavra, se `has_photo` está
certo:

```bash
python manage.py check_photos
```

## Deploy

### Railway

1. No painel do Railway, crie um serviço a partir deste repositório
   (raiz do repo — não precisa apontar subpasta nenhuma).
2. Adicione um banco **PostgreSQL** ao projeto (Railway cria e injeta
   `DATABASE_URL` sozinho).
3. Defina as variáveis de ambiente do serviço (veja `.env.example`):
   `DJANGO_SECRET_KEY` (gere uma nova, aleatória), `DJANGO_DEBUG=False`,
   `DJANGO_ALLOWED_HOSTS=seu-app.up.railway.app`.
4. O `Procfile` já define o build/start (`release: migrate`,
   `web: gunicorn idiomas_site.wsgi`). O Railway detecta Python
   automaticamente pelo `requirements.txt` na raiz.
5. Depois do primeiro deploy, rode uma vez pelo console do serviço:
   ```bash
   python manage.py import_words
   python manage.py createsuperuser
   ```

### Render / outro serviço de Python

Mesma ideia: build `pip install -r requirements.txt && python manage.py collectstatic --noinput`,
start `gunicorn idiomas_site.wsgi --log-file -`, banco PostgreSQL
próprio do provedor, variáveis de ambiente iguais às do Railway acima.

Estático (CSS/JS) é servido pelo próprio Django via WhiteNoise — não
precisa de Vercel/Netlify nem de configurar nada à parte.

## Próximos passos possíveis

Veja `prompts/melhorar-sistema.md` — prompt pronto pra pedir a uma IA
que analise o estado atual e priorize as próximas melhorias.

- **Espanhol/Francês** — o seletor de idioma já existe na UI; falta
  adicionar as traduções no `Word` (hoje só há `en`) e um campo pra
  escolher o idioma alvo por usuário.
- **Vender depois** — dá pra adicionar um campo `plan` no `Profile` e
  checar nas views antes de liberar tópicos "premium"; o Django admin já
  serve pra gerenciar isso manualmente antes de automatizar cobrança.
