Você vai analisar um sistema de flashcards de idiomas já em produção e propor as próximas melhorias, priorizadas por impacto.

## O sistema

"Caderno de Idiomas" é um app de flashcards para praticar vocabulário
português → inglês, em produção real (Railway, domínio próprio
`cadernodeidiomas.co.uk`) com usuário real usando no dia a dia. Stack:
Django (Python), banco relacional (SQLite em dev, PostgreSQL em
produção), templates server-side + JavaScript vanilla para a interação
do cartão e TTS. Sem framework de frontend, sem SPA.

Modelos principais:
- `Topic` (tópico: slug, nome, emoji, ordem)
- `Word` (pt, en, tópico, `has_photo`, `photo_url`/`photo_page`/`photo_credit`
  cacheados, `photo_variants` com alternativas)
- `Progress` (usuário, palavra, `level` 0–4, `next_review`, `last_wrong_answer`)
- `Profile` (usuário, sequência de dias estudados, `ai_analysis` JSON
  estruturado gerado pelo coach de IA, `last_activity_at`)

Fluxo de uso: o usuário cria conta (e-mail + senha, com recuperação de
senha por e-mail via Resend), vê um dashboard com anel de progresso
(palavras dominadas / total), sequência de dias, um nível CEFR calculado
a partir de palavras dominadas (A1–C2, com barra de progresso pro
próximo nível — ver `flashcards/levels.py`), uma análise de IA sempre
visível em 3 seções (pontos fortes / foco / recomendação — gerada no
máximo 1x por hora de atividade, Gemini como modelo principal e Groq
como fallback, ver `flashcards/ai_coach.py`), um widget de "N revisões
vencidas" que leva direto pro tópico mais crítico, e uma lista de
tópicos com busca e filtros (todos / em progresso / dominados / não
iniciados).

Ao entrar num tópico, a sessão já vem filtrada só com o que está vencido
ou nunca foi visto — repetição espaçada tipo Leitner leve (níveis 0 a 4,
intervalos 1/3/7/15/30 dias). Se nada está vencido, mostra "tudo em dia"
com CTA útil (praticar tudo mesmo assim / ver palavras) em vez de forçar
estudo ou deixar o usuário num beco sem saída. A página do tópico
também explica em linguagem simples como funciona a revisão espaçada e
mostra a data da próxima revisão por palavra.

Cada cartão mostra a palavra em português ou (se `has_photo=true` e a
URL já está cacheada) uma foto real do conceito — sem round-trip pra
Pexels/Wikipedia na maioria das vezes. A opção "Foto" nem aparece se o
tópico não tem nenhuma palavra fotografável. O aluno digita a tradução
num campo sempre visível e obrigatório (o botão "Conferir" fica
desabilitado até haver texto — não dá pra "pular" sem tentar, isso já
foi um bug corrigido de propósito), vê se errou a mesma palavra da
última vez, e responde com 3 níveis — Errei / Quase / Sabia — com
atalhos de teclado 1/2/3. Ao revelar a resposta, toca automaticamente a
pronúncia em inglês via Web Speech API (`SpeechSynthesisUtterance`,
zero custo, zero arquivo de áudio armazenado) com botão pra repetir.
Erros da rodada podem ser revisados na hora, sem sair do tópico.

Pipeline de fotos (`flashcards/photos.py`): busca no Pexels, rankeia
candidatos por texto alternativo (penaliza fotos artísticas/editoriais,
pessoas em primeiro plano quando a palavra não é sobre pessoa, sentidos
ambíguos por palavra), cai pra Wikipedia quando não há candidato bom. A
validação final usa Gemini Vision (`gemini-flash-lite-latest`) só
quando o candidato por texto não é confiável o suficiente (~20% das
palavras na prática) — desenhado assim de propósito pra escalar pra
milhares de palavras sem gastar quota checando toda palavra visualmente
nem depender de curadoria manual palavra por palavra.

Já existe: autenticação completa (cadastro, login, recuperação de senha
com throttling por IP e e-mail HTML com a identidade visual do app,
troca de senha), painel de administração do Django pra gerenciar
tópicos/palavras sem código (com exportação CSV), importador que aceita
JSON ou CSV, comando `check_photos` que popula/revalida fotos em lote,
17 testes automatizados, hardening de segurança pra produção (HTTPS,
cookies seguros, HSTS, CSRF configurado pro proxy do Railway).

Já foi decidido e não deve ser revisitado sem motivo forte: nada de
emoji como estímulo de aprendizagem (só foto real ou texto); nenhum modo
"misturar" palavra/foto; o campo de digitação/recall sempre ativo e
obrigatório (nunca opcional, nunca revela a resposta sem tentativa);
repetição espaçada simples tipo Leitner (não pedir SM-2/Anki completo —
decisão consciente de manter transparente e fácil de manter); TTS via
Web Speech API do navegador, não arquivo de áudio permanente por
palavra; validação de foto em duas camadas (texto primeiro, Vision só
quando necessário) — não trocar por "Vision em toda palavra sempre".

## Sua tarefa

Aja como um product designer + engenheiro sênior especializado em
produtos de aprendizagem (memorização espaçada, recall ativo, UX de
estudo) — não como um gerador de lista de features genéricas.

1. Aponte de 5 a 8 melhorias concretas, cada uma com: o que é, por que
   importa (que problema real de aprendizagem ou de produto resolve), e
   como encaixaria na arquitetura acima (em que modelo/view/template/
   arquivo mexeria).
2. Priorize por impacto no aprendizado real do usuário, não por
   "impressionar visualmente". O SRS básico, o coach de IA, o TTS e a
   validação de fotos já existem — pense no que vem depois deles (ex:
   refinar os intervalos com dados reais de acerto, evitar sobrecarga
   quando muitas revisões vencem no mesmo dia, detectar palavras que o
   aluno erra repetidamente e tratar diferente, melhorar a qualidade do
   feedback da IA com mais sinal, etc.), não em reconstruir do zero o
   que já funciona.
3. Para cada ideia, diga explicitamente se ela é simples (poucas horas),
   média ou complexa — não proponha arquitetura sofisticada onde uma
   solução simples resolve.
4. Não sugira reintroduzir emoji como estímulo de aprendizagem, nem um
   modo "misturar" palavra/foto, nem tornar o campo de recall opcional,
   nem trocar o Leitner leve por um SM-2/Anki completo, nem trocar o TTS
   em tempo real por áudio pré-gravado, nem rodar Gemini Vision em toda
   palavra — essas decisões já foram tomadas de propósito.
5. Termine com as 2 mudanças que você faria primeiro, se só pudesse
   fazer duas.

Seja direto e específico. Nada de "melhorar a UX em geral" — cada
sugestão precisa ser algo que dá pra implementar.
