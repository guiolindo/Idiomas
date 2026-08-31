Você vai analisar um sistema de flashcards de idiomas já em produção e propor as próximas melhorias, priorizadas por impacto.

## O sistema

"Caderno de Idiomas" é um app de flashcards para praticar vocabulário
português → inglês. Stack: Django (Python), banco relacional (SQLite em
dev, PostgreSQL em produção), templates server-side + um pouco de
JavaScript vanilla para a interação do cartão. Sem framework de frontend.

Modelos principais:
- `Topic` (tópico: slug, nome, emoji, ordem)
- `Word` (pt, en, tópico, `has_photo` — se faz sentido mostrar foto)
- `Progress` (usuário, palavra, sabia/não sabia, data)
- `Profile` (usuário, sequência de dias estudados)

Fluxo de uso: o usuário cria conta (e-mail + senha), vê um dashboard com
progresso geral, sequência de dias e uma lista de tópicos com busca e
filtros (todos / em progresso / dominados / não iniciados). Ao entrar num
tópico, estuda cartão por cartão: vê a palavra em português ou (se a
palavra tem `has_photo=true`) uma foto real do conceito, buscada ao vivo
na Wikipedia. A opção "Foto" só aparece pro aluno se pelo menos uma
palavra do tópico tiver `has_photo=true` — tópicos só de palavras
abstratas (preposições, pronomes) nem mostram essa opção. O aluno digita
a tradução em inglês num campo sempre visível (não é opcional), recebe
uma correção tolerante a acento e pequenos erros de digitação, e marca
"sabia" ou "errei". Erros da rodada podem ser revisados na hora. Existe
um filtro "só o que ainda não sei" por tópico.

Já existe: autenticação completa (cadastro, login, recuperação de senha,
troca de senha), painel de administração do Django pra gerenciar
tópicos/palavras sem código (com exportação CSV), importador que aceita
JSON ou CSV, um comando (`check_photos`) que verifica empiricamente na
Wikipedia se cada palavra tem foto e ajusta `has_photo` sozinho, 13
testes automatizados, hardening de segurança para produção (HTTPS,
cookies seguros, HSTS).

Já foi decidido e não deve ser revisitado sem motivo forte: nada de
emoji como estímulo de aprendizagem (só foto real ou texto — emoji foi
removido de propósito, inclusive o modo "Misturar" palavra/foto, que
existiu brevemente e foi removido por não ter serventia real); o campo
de digitação/recall fica sempre ativo (não é um modo opcional que
precisa ser ligado).

## Sua tarefa

Aja como um product designer + engenheiro sênior especializado em
produtos de aprendizagem (memorização espaçada, recall ativo, UX de
estudo) — não como um gerador de lista de features genéricas.

1. Aponte de 5 a 8 melhorias concretas, cada uma com: o que é, por que
   importa (que problema real de aprendizagem ou de produto resolve), e
   como encaixaria na arquitetura acima (em que modelo/view/template
   mexeria).
2. Priorize por impacto no aprendizado real do usuário, não por
   "impressionar visualmente". Coisas como repetição espaçada de verdade
   (baseada em histórico de acerto/erro, não só "sabia/não sabia" binário),
   dificuldade adaptativa, e revisão inteligente valem mais que
   decoração.
3. Para cada ideia, diga explicitamente se ela é simples (poucas horas),
   média ou complexa — não proponha arquitetura sofisticada onde uma
   solução simples resolve.
4. Não sugira reintroduzir emoji como estímulo de aprendizagem, nem um
   modo "misturar" palavra/foto, nem tornar o campo de recall opcional
   — essas três coisas já foram tentadas e removidas de propósito.
5. Termine com as 2 mudanças que você faria primeiro, se só pudesse
   fazer duas.

Seja direto e específico. Nada de "melhorar a UX em geral" — cada
sugestão precisa ser algo que dá pra implementar.
