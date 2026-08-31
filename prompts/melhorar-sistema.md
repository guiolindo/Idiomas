Você vai analisar um sistema de flashcards de idiomas já em produção e propor as próximas melhorias, priorizadas por impacto.

## O sistema

"Caderno de Idiomas" é um app de flashcards para praticar vocabulário
português → inglês. Stack: Django (Python), banco relacional (SQLite em
dev, PostgreSQL em produção), templates server-side + um pouco de
JavaScript vanilla para a interação do cartão. Sem framework de frontend.

Modelos principais:
- `Topic` (tópico: slug, nome, emoji, ordem)
- `Word` (pt, en, tópico, `has_photo`, `photo_url`/`photo_page` cacheados)
- `Progress` (usuário, palavra, `level` 0–4, `next_review`, `last_wrong_answer`)
- `Profile` (usuário, sequência de dias estudados)

Fluxo de uso: o usuário cria conta (e-mail + senha), vê um dashboard com
anel de progresso (palavras dominadas / total), sequência de dias, um
widget de "N revisões vencidas" (quando existem) que já leva direto pro
tópico mais crítico, e uma lista de tópicos com busca e filtros (todos /
em progresso / dominados / não iniciados). Ao entrar num tópico, a
sessão já vem filtrada só com o que está vencido ou nunca foi visto —
repetição espaçada tipo Leitner leve (níveis 0 a 4, intervalos 1/3/7/15/30
dias). Se nada está vencido, mostra "tudo em dia" em vez de forçar
estudo. Cada cartão mostra a palavra em português ou (se `has_photo=true`
e a URL já está cacheada por `check_photos`) uma foto real do conceito —
sem round-trip pra Wikipedia na maioria das vezes. A opção "Foto" nem
aparece se o tópico não tem nenhuma palavra fotografável (preposições,
pronomes etc). O aluno digita a tradução num campo sempre visível (não é
opcional), vê se errou a mesma palavra da última vez ("você escreveu X
da última vez"), e responde com 3 níveis — Errei (nível 0, revisão
amanhã) / Quase (mantém nível, revisão amanhã) / Sabia (sobe de nível,
intervalo maior) — com atalhos de teclado 1/2/3. Erros da rodada podem
ser revisados na hora, sem sair do tópico.

Já existe: autenticação completa (cadastro, login, recuperação de senha,
troca de senha), painel de administração do Django pra gerenciar
tópicos/palavras sem código (com exportação CSV), importador que aceita
JSON ou CSV, um comando (`check_photos`) que verifica empiricamente na
Wikipedia se cada palavra tem foto (e cacheia a URL) em vez de adivinhar,
17 testes automatizados, hardening de segurança para produção (HTTPS,
cookies seguros, HSTS).

Já foi decidido e não deve ser revisitado sem motivo forte: nada de
emoji como estímulo de aprendizagem (só foto real ou texto); nenhum modo
"misturar" palavra/foto; o campo de digitação/recall sempre ativo (nunca
opcional); repetição espaçada simples tipo Leitner (não pedir SM-2/Anki
completo — decisão consciente de manter transparente e fácil de manter).

## Sua tarefa

Aja como um product designer + engenheiro sênior especializado em
produtos de aprendizagem (memorização espaçada, recall ativo, UX de
estudo) — não como um gerador de lista de features genéricas.

1. Aponte de 5 a 8 melhorias concretas, cada uma com: o que é, por que
   importa (que problema real de aprendizagem ou de produto resolve), e
   como encaixaria na arquitetura acima (em que modelo/view/template
   mexeria).
2. Priorize por impacto no aprendizado real do usuário, não por
   "impressionar visualmente". O SRS básico já existe — pense no que vem
   depois dele (ex: refinar os intervalos com dados reais de acerto,
   evitar sobrecarga quando muitas revisões vencem no mesmo dia, etc.),
   não em reconstruí-lo do zero.
3. Para cada ideia, diga explicitamente se ela é simples (poucas horas),
   média ou complexa — não proponha arquitetura sofisticada onde uma
   solução simples resolve.
4. Não sugira reintroduzir emoji como estímulo de aprendizagem, nem um
   modo "misturar" palavra/foto, nem tornar o campo de recall opcional,
   nem trocar o Leitner leve por um SM-2/Anki completo — essas decisões
   já foram tomadas de propósito.
5. Termine com as 2 mudanças que você faria primeiro, se só pudesse
   fazer duas.

Seja direto e específico. Nada de "melhorar a UX em geral" — cada
sugestão precisa ser algo que dá pra implementar.
