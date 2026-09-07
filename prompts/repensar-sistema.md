Você vai olhar pra um app de flashcards de idiomas em produção e propor uma
**visão ambiciosa** do que ele pode virar. Não quero "próximas 5 features" —
quero um projeto de produto que faça o app deixar de ser "flashcard estilo
Anki simpático" e virar uma ferramenta que uma pessoa entrando pela primeira
vez pense "ah, isso aqui é diferente de tudo que já testei".

Assuma que sou um engenheiro sênior sozinho no projeto, com um usuário beta
ativo (meu irmão), e que tenho autonomia total sobre o roadmap. Fale de
igual pra igual — não me poupe de ideias grandes achando que eu não vou
conseguir; se a ideia for grande, me diga como quebrar em fases.

## O que o app é hoje

"Caderno de Idiomas" — flashcards PT → EN. Já em produção real com domínio
próprio (`cadernodeidiomas.co.uk`) e usuário ativo. Django + Postgres,
templates server-side + JS vanilla, hospedado em Railway. Sem framework de
frontend, sem SPA — decisão consciente pra manter simples de manter sozinho.

O que já existe e funciona:

- Repetição espaçada tipo Leitner leve (níveis 0–4, intervalos 1/3/7/15/30
  dias), com cap diário de 35 revisões por sessão pra não sobrecarregar
- Recall ativo obrigatório (o campo de digitação nunca é opcional; o botão
  "Conferir" só ativa quando há texto)
- Tolerância a gralhas (distância de Levenshtein no cliente reconhece
  "aple" como "Quase" e não como erro completo)
- Detecção de leech (palavras com 3+ erros seguidos ganham marca visual
  e o coach de IA passa a citá-las por nome)
- TTS ao revelar a resposta via Web Speech API do navegador
  (`SpeechSynthesisUtterance`, zero custo, zero storage), com botão pra
  repetir e seleção automática da melhor voz do sistema
- Fotos reais dos conceitos (Pexels rankeado por texto alternativo,
  Wikipedia como fallback, validação com Gemini Vision só nos casos
  ambíguos — ~20% das palavras — pra escalar sem gastar quota)
- Coach de IA sempre visível na home em 3 seções (pontos fortes / foco /
  recomendação), regenerado no máximo 1x por hora de atividade, Gemini
  principal e Groq como fallback
- Nível CEFR calculado a partir de palavras dominadas (A1 → C2, com barra
  de progresso pro próximo nível)
- Feedback pós-rodada específico pela IA ("os três erros foram verbos")
- Autenticação completa (cadastro, login, recuperação de senha via Resend
  com e-mail HTML da identidade visual do app)
- ~2500 palavras cadastradas em ~30 tópicos, com painel admin do Django

O design atual é "caderno de caneta-tinteiro" — papel kraft (#F7EFDC),
margem vermelha vertical, tipografia serifada, indigo (#1F3157) como
acento. Funciona, mas o próprio usuário já disse "achei meio feio", então
essa parte também está no escopo de repensar.

## O que já foi decidido de propósito (não revisitar)

- Recall ativo sempre obrigatório — não voltar pra "só clicar em Sabia"
- Leitner leve, não SM-2/Anki completo — transparência importa mais que
  otimização de intervalos
- TTS em tempo real via navegador, não áudio pré-gravado por palavra
- Fotos por Pexels/Wikipedia com Vision seletivo, não Vision em todas
- Django monolito + JS vanilla no cliente, não SPA/framework
- Custo baixo: qualquer proposta que precise de infra paga por usuário tem
  que valer muito a pena e ser opcional

## Sua tarefa

Escreva uma **visão de produto** — não uma lista de features soltas. Comece
com o pitch em duas frases: "hoje o app é X, daqui a 6 meses ele é Y". Aí
detalhe.

Considere expandir em qualquer combinação destas dimensões (e proponha
outras que eu não pensei):

- **Fala do aluno** — pronúncia via `SpeechRecognition` do navegador (grátis,
  zero servidor), pontuada e integrada ao SRS. O usuário grava, o sistema
  diz se a pronúncia bateu e conta pontos. Como isso muda o loop de estudo?
- **Escuta ativa** — o oposto do TTS atual: o app fala, o aluno digita o que
  ouviu. Dictation. Diferente de recall visual, treina outro canal.
- **Frases contextuais geradas por IA** — em vez de só palavra solta, a IA
  gera uma frase curta usando 2-3 palavras que o aluno já aprendeu (spaced
  retrieval em contexto). Isso pode virar cartão novo? Modo alternativo?
- **Escrita livre com correção** — 3 linhas em inglês sobre o que fez hoje,
  IA aponta erros específicos. Zero-custo? Cabe no loop diário?
- **Adaptação temporal** — sessão de 3 minutos no ônibus ≠ sessão de 20
  minutos em casa. O app deveria perguntar quanto tempo tem?
- **Ancoragem em conteúdo real** — legendas de filmes, letras de música,
  manchetes do dia. Como ganchar o vocabulário aprendido em algo que o
  aluno já consome?
- **Redesenho visual** — se o "caderno" não está agradando, o que faria
  sentido? Não uma "correção" — uma direção de arte diferente, coerente
  com o produto, defendida em 2-3 frases.
- **Rituais e ritmo** — hoje o único ritual é "abre e estuda". Um app bom
  cria momentos: revisão da manhã, resumo semanal, marcos claros.
- **Multiusuário/social** — vale? Fere o "sistema simples pra manter"? Se
  vale, em que dose (comparar progresso? deck compartilhado?)?

## Formato da resposta

1. **Pitch** (2 frases) — o antes/depois do produto
2. **Princípios** (3-5) — o que o app defende e o que rejeita, em uma linha
   cada. Isso é o que separa produto bom de "coleção de features"
3. **Módulos novos** (3-6) — cada um com: o que é, por que muda a
   experiência de verdade (não "melhora"), como se encaixa no loop
   existente, complexidade honesta (S/M/L/XL) e se depende de custo novo
   (quota de IA extra, storage etc)
4. **Direção visual** — 3-4 frases descrevendo um redesenho: paleta,
   tipografia, sensação. Se defender manter o "caderno", explique por quê
5. **Roadmap fásico** — se eu só puder fazer 1 módulo em cada uma das
   próximas 3 sprints (uma sprint = 1-2 semanas de dev noturno), quais e
   por que nessa ordem
6. **O corte cruel** — uma coisa que hoje existe no app que você tiraria
   ou reformularia radicalmente, e por quê. Se não houver, diga

Não invente números ("aumenta retenção em 47%"). Fale como product designer
sênior conversando com um engenheiro, não como vendedor.
