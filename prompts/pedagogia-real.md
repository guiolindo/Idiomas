Você vai fazer uma pesquisa aplicada sobre **como pessoas realmente aprendem um idioma** (não como aprendem em cursos comerciais), com o objetivo de me ajudar a transformar um app de flashcards em uma ferramenta séria de aprendizado.

Aja como pesquisador de aquisição de segunda língua (Applied Linguistics / SLA — Second Language Acquisition) conversando com um engenheiro que constrói um app pequeno, pessoal, sem investidores. Sem tom de vendedor, sem "boas práticas" genéricas. Cite fontes reais quando existirem — Krashen, VanPatten, Nation, Ellis, Lightbown & Spada, Council of Europe descriptors — e diga o que é opinião sua.

Se algo é debate aberto no campo, diga que é debate. Se algo é consenso empírico razoável, diga que é. Não invente números. Se não souber, diga que não sabe.

## O produto hoje

"Caderno de Idiomas" — flashcards português → inglês, em produção real com usuário ativo. Django + Postgres, JS vanilla no cliente. Repositório público: github.com/guiolindo/Idiomas. Site: cadernodeidiomas.co.uk.

**O que já existe:**

- Repetição espaçada tipo Leitner leve, 5 níveis, intervalos fixos 1/3/7/15/30 dias
- Recall ativo obrigatório (digitação ou fala — nunca "clicar em sabia")
- 4 modos de exercício:
  - **Escrita**: vê palavra em PT (ou uma foto), escreve em EN
  - **Ditado**: ouve em EN, escreve a tradução em PT (compreensão auditiva)
  - **Transcrição**: ouve em EN, escreve em EN (spelling)
  - **Voz**: vê em PT, fala em EN (produção oral via SpeechRecognition do navegador)
- Detecção de palavras travadas (leech — 3+ erros seguidos)
- Cap diário por sessão (5/15/35 cartões, o aluno escolhe pelo tempo)
- Nível CEFR calculado por vocabulário dominado (A1→C2)
- Coach de IA (Gemini + Groq) analisa pontos fortes / foco / recomendação em 3 seções, gerado no fim de cada rodada
- Feedback com diff tipográfico (letras certas em tinta, extras riscadas, faltantes sublinhadas)
- Fotos reais dos conceitos (Pexels + Wikipedia, validadas seletivamente por Gemini Vision)
- Streak, palavra do dia, desafio relâmpago, dashboard de leech
- ~2500 palavras em ~92 tópicos por tema (Pessoas, Corpo, Comida, Verbos, etc)

**Restrições que ficam:**

- Custo baixo (não pode virar Duolingo Plus)
- Django server-side, JS vanilla — sem framework de frontend
- Feito por 1 engenheiro sozinho no tempo livre
- Usuário atual: irmão do dev, iniciante em inglês

## O que quero que você entregue

Estrutura da resposta, nessa ordem:

### 1. Fundamentos científicos (o consenso e os debates)

Explique em linguagem direta o que a pesquisa em SLA diz que **realmente funciona** pra adulto brasileiro aprender inglês. Cubra pelo menos:

- **Comprehensible input** (Krashen i+1) — o que é, por que é a espinha, o que muitos apps ignoram
- **Ordem natural de aquisição** — o que vem antes do quê, o que não adianta forçar
- **Silent period** — a fase de escutar antes de produzir. Precisamos respeitar isso?
- **Produção precoce vs. output útil** (Swain output hypothesis) — quando forçar produção ajuda e quando atrapalha
- **Notice hypothesis** (Schmidt) — o papel da atenção consciente
- **Interlanguage** — por que a pessoa erra "sistematicamente" e o que isso diz sobre a curva
- **Papel da gramática explícita vs implícita** — o que se aprende regra decorada, o que se aprende por exposição
- **Frequência lexical** — quantas palavras cobrem quanto de fala real? (cite Nation, BNC)

Um parágrafo por tema, sem enrolação. Se algum tema for irrelevante pro app, diga por quê.

### 2. Como uma pessoa real aprende inglês do zero até B2 (fluxo)

Descreva o cronograma realista pra um adulto brasileiro dedicando 20-40 min/dia, do zero ao B2 (nível "consigo trabalhar em inglês"). Diga:

- Quanto tempo até A2, B1, B2 (com fonte se existir — CEFR self-assessment, EF EPI)
- Quais atividades dominam em cada fase (mais listening no início, mais output no meio, mais reading no fim?)
- Marcos concretos do usuário — o que ele consegue fazer em cada nível
- Sinais de que é hora de mudar de fase

### 3. O que os apps líderes acertam e erram

Diagnóstico honesto de Duolingo, Anki, Babbel, Memrise, LingoDeer, Pimsleur:
- O que cada um faz bem (não elogio genérico — cite o mecanismo)
- Onde cada um enrola o usuário (gamification vazio, ilusão de progresso, etc)
- Qual a lição prática pra um app pequeno como o meu

### 4. Diagnóstico do Caderno de Idiomas hoje

Contra o que a pesquisa mostra em (1) e (2):
- **O que ele acerta.** Onde já está alinhado com a ciência.
- **O que ele erra.** Onde a atual arquitetura contradiz o que funciona.
- **O que falta.** Peças pedagógicas essenciais que não existem — nomear cada uma.

Não me poupe. Se o que eu construí é bom só pra memorização de vocabulário e não pra "aprender inglês de verdade", diga isso e diga o que precisa mudar.

### 5. Plano pedagógico concreto

Um fluxo de uso de 20-40 min/dia pra alguém iniciante, usando o que **já existe** no app + o que **precisa ser adicionado**. Formato:

- **Fase 1 (semanas 1-4, A1 inicial)**: X min de Y, Z min de W
- **Fase 2 (semanas 5-16, A1→A2)**: ...
- **Fase 3 (meses 5-9, A2→B1)**: ...
- **Fase 4 (mês 10+, B1→B2)**: ...

Para cada fase, diga:
- Quais atividades do app usar e em que proporção
- O que **falta** no app pra essa fase (input compreensível de nível certo? leitura graded? shadowing? escrita livre?)
- Como medir se o aluno tá progredindo naquela fase (não só "palavras dominadas" — que outros sinais?)

### 6. Módulos novos priorizados (o que construir a seguir)

Lista de 3-5 módulos NOVOS que fariam o app virar ferramenta profissional. Para cada:
- **O que é** em uma linha
- **Por que é essencial** (referência à ciência)
- **Complexidade honesta** (S/M/L)
- **Custo** (grátis, quota de IA, storage)
- **Como se encaixa no fluxo (5)**

Priorize em ordem — o primeiro é o mais transformador.

### 7. Métricas do que realmente importa

Hoje o app mede: palavras dominadas, streak, nível CEFR estimado, palavras travadas. Do ponto de vista de SLA:

- Essas métricas são úteis? Enganam?
- Que outras métricas deveriam existir pra medir aprendizado real, não engagement?
- Um "score de proficiência" honesto teria que incluir o quê?

### 8. O corte cruel

Uma coisa no app atual que — segundo a pesquisa — está ativamente **atrapalhando** o aprendizado (não só irrelevante, mas negativa) e deveria ser removida ou reformulada. Se não houver, diga.

## Formato

- Português brasileiro, tom direto
- Cite fonte quando existir (livro, autor, ano) — mesmo curto: "(Krashen 1985)"
- Se especular, marque: "opinião minha"
- Números concretos onde houver: "500 palavras cobrem ~60% do inglês falado (Nation 2013)"
- Sem "seria bom ter" solto — sempre amarrado ao mecanismo pedagógico
