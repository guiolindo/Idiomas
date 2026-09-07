Você é um designer de UI/UX sênior, especializado em produtos de consumo. Vou te descrever um app em produção e pedir uma revisão visual e sistêmica — não de features (o produto já tem tudo que precisa por enquanto), mas de **linguagem visual, hierarquia, tipografia, cores, densidade e sensação geral**.

Fale como designer conversando com o engenheiro sozinho por trás do produto. Sem paciência com decoração cerimonial e sem indulgência com decisões preguiçosas. Se algo hoje está genérico, diga. Se algo está no caminho certo mas mal executado, diga o que falta.

## O produto

"Caderno de Idiomas" — flashcards português → inglês. Em produção real com usuário ativo (`cadernodeidiomas.co.uk`, hospedado no Railway). Django + Postgres, templates server-side + JS vanilla no cliente, sem framework de frontend. Repositório público: github.com/guiolindo/Idiomas.

Vocabulário de ~2500 palavras em ~30 tópicos. Repetição espaçada tipo Leitner (5 níveis, intervalos fixos). Recall ativo obrigatório (digitação ou fala — nunca "clica em sabia" sem provar).

## O que existe visualmente hoje

**Metáfora escolhida:** "caderno de caneta-tinteiro". Papel kraft (#EDE2C7 e #F7EFDC), margem vermelha vertical (#B44231) em cartões-chave, tipografia serifada (Fraunces como display, Instrument Serif como itálico ornamental), acento indigo (#1F3157), ouro (#9E7226) pra secundário. Tema escuro invertendo os tons.

**Elementos-chave:**
- Home com hero de saudação ("Boa noite, Nome."), card de nível CEFR (A1–C2), anel de progresso, análise de IA em 3 seções, banner "Continuar estudando" ou "N revisões vencidas", palavra do dia, cards de "Desafio relâmpago" e "Palavras travadas", grid de tópicos e busca/filtros.
- Cards de tópico como "índice de caderno": número serifado grande (01, 02...), título em serifa, barra de progresso fina, margem vermelha lateral. Sem emoji (foram removidos porque colidiam com a paleta e tinham métricas inconsistentes).
- Tela de estudo com "cartão" tipo página pautada (linhas horizontais suaves, margem vermelha), campo de digitação como "caderno de resposta", 3 botões após revelar (Errei / Quase / Sabia).
- Menu de conta como dropdown no header. Rodapé com links pra Ajuda, Sobre, Termos, Código-fonte.
- Páginas de documento (Ajuda, Sobre, Termos) em layout de coluna estreita, tipografia serifada grande.

**Modalidades de estudo:** Escrita (padrão, vê PT ou foto, escreve EN), Ditado (ouve EN, escreve PT), Voz (vê PT, fala EN via SpeechRecognition do navegador).

## O que o usuário reclamou até aqui

- "Parece app genérico, tipo esses 500 que são feitos por dia."
- "Está meio feio, sem identidade."
- "Coisas sobrepostas, alinhamento estranho." (Alguns bugs eu já corrigi — colisões de classes CSS.)
- "Emoji nos cards ficava fora do lugar." (Removi por completo, agora usa numeração serifada.)
- "Poucas coisas pra clicar, sistema monótono." (Adicionei desafio, palavra do dia, dashboard de travadas, mas isso é feature — não design.)

## O que já foi decidido e não deve ser revisitado

- Django server-side + JS vanilla — nada de framework de frontend
- Recall ativo obrigatório (digitação ou voz), nunca opcional
- Leitner leve (não SM-2/Anki)
- Tema claro **e** escuro, ambos precisam ter a mesma qualidade
- Google Fonts é o único CDN de fonte disponível (restrição do host)

## O que quero de você

Não uma lista de "seria bom ter" — quero **direção clara**. Estrutura da resposta:

1. **Diagnóstico honesto (3-5 frases).** O que o app parece hoje pra quem chega frio? Onde ele acerta e onde entrega genérico? Não me poupe.

2. **Vale a pena manter a metáfora "caderno"?** Se sim, o que precisa mudar pra ela realmente aparecer (não só existir como decoração)? Se não, o que substitui e por quê? Argumente.

3. **Sistema de cores.** A paleta atual (kraft/indigo/margem-vermelha/ouro) funciona ou é preciso repensar? Se manter, o que ajustar (contraste, saturação, quando usar cada acento). Se trocar, proponha uma alternativa concreta com hex codes.

4. **Sistema tipográfico.** Fraunces + Instrument Serif + IBM Plex Mono está bem casado? Que hierarquia clara você propõe (h1/h2/h3, corpo, meta, mono) — tamanhos e usos específicos.

5. **Grid e densidade da home.** Hoje tem hero + level + ring + análise IA + banner + palavra do dia + ações rápidas + busca + filtros + grid de tópicos + rodapé. É demais? Se é, o que corta/agrupa? Se cabe, como organizar visualmente pra não parecer feed.

6. **Cartão de estudo.** O elemento central do app. Analise: layout, hierarquia, ritmo, sensação. O que faria ele parecer premium em vez de utilitário?

7. **Micro-interações e ritmo.** Onde o app hoje é morto (transições, feedback de acerto/erro, momento de revelar resposta, fim de rodada) e onde deveria ter mais vida (sem virar cerimônia).

8. **Tema escuro.** Ele tá bom hoje ou é só uma inversão preguiçosa das cores claras? Se preguiçoso, o que faz um dark mode real pra este produto?

9. **O corte cruel.** Uma coisa no visual atual que você tiraria hoje sem pensar.

10. **Referências.** 2-3 produtos ou peças de design (nome + o que copiar deles) que serviriam de norte pra este redesign.

Seja concreto. Se citar "aumentar padding", diga de quanto pra quanto. Se citar tipografia, diga qual fonte substitui qual. Se propor cor, dê hex. O engenheiro que vai implementar precisa saber exatamente o que fazer.
