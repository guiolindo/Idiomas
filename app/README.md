# Caderno de Idiomas

Flashcards de vocabulário PT → outros idiomas, com modo emoji, foto real
(Wikimedia) e modo caderno para forçar o recall.

## Estrutura

```
app/
  backend/          FastAPI — serve os dados e faz proxy de imagem
    main.py
    requirements.txt
    .env.example
  frontend/         HTML/CSS/JS puro — nenhum framework, nenhum build
    index.html
    css/style.css
    js/app.js
  data/
    words.json      fonte única dos tópicos e palavras
  supabase/
    schema.sql       tabela de progresso por usuário (para quando ligar login)
```

Por que separado: o front nunca fala com a Wikimedia nem guarda segredo
nenhum — ele só fala com o backend. Isso deixa livre pra depois trocar o
provedor de imagem, adicionar login, adicionar paywall, etc., sem mexer
no front.

## Rodando localmente

**Backend**
```bash
cd app/backend
python -m venv .venv
.venv/Scripts/activate        # no Windows; no Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Frontend** — é só abrir `app/frontend/index.html` no navegador, ou servir
com qualquer servidor estático:
```bash
cd app/frontend
python -m http.server 5500
```
Depois abra `http://localhost:5500`. O `index.html` já aponta para
`http://localhost:8000` (veja a linha `window.API_BASE` no fim do arquivo).

## Deploy grátis

| Peça | Onde | Por quê |
|---|---|---|
| Backend (FastAPI) | [Render](https://render.com) ou [Railway](https://railway.app) — free tier | sobe direto de um repo Git, HTTPS de graça |
| Frontend (estático) | [Vercel](https://vercel.com) ou [Netlify](https://netlify.com) | arrasta a pasta `frontend/` e pronto |
| Banco + login | [Supabase](https://supabase.com) — free tier | Postgres + Auth prontos, sem servidor próprio |

Passos:
1. Suba este repositório no GitHub.
2. No Render/Railway: novo Web Service apontando pra `app/backend`, comando
   de start `uvicorn main:app --host 0.0.0.0 --port $PORT`.
3. No Vercel/Netlify: novo projeto apontando pra `app/frontend`. Depois do
   deploy, edite `window.API_BASE` no `index.html` pra URL do backend.
4. Crie um projeto no Supabase, rode `supabase/schema.sql` no SQL Editor,
   copie a URL e a anon key pro `.env` do backend (veja `.env.example`).

## Próximos passos (login e "vender depois")

O backend já tem o esqueleto em `POST /api/progress/{topic}/{word}` esperando
um token do Supabase Auth. Falta:

1. No front, adicionar o Supabase JS SDK e uma tela de login (magic link ou
   Google) — o Supabase cuida de senha, sessão e segurança.
2. Trocar `localStorage` por chamadas pra esse endpoint, mandando
   `Authorization: Bearer <token>`.
3. Se um dia quiser vender: uma coluna `plan` na tabela `auth.users` (ou uma
   tabela `subscriptions`) e checar no backend antes de liberar tópicos
   premium. Pagamento por Stripe tem free tier de integração (só cobra %
   por transação).

Nada disso precisa ser feito agora — o app funciona 100% sem login hoje.
