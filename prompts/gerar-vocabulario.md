Você vai expandir o banco de vocabulário de um app de flashcards português → inglês, gerando um arquivo pronto pra importar (JSON ou CSV — veja as duas opções abaixo).

## Formato de saída — opção 1: JSON

```json
{
  "topics": [
    {
      "id": "frutas",
      "name": "Frutas e vegetais",
      "emoji": "🍎",
      "words": [
        {"pt": "maçã", "en": "apple", "has_photo": true},
        {"pt": "usar", "en": "to use", "has_photo": false}
      ]
    }
  ]
}
```

## Formato de saída — opção 2: CSV

Se preferir (ou se o JSON ficar grande demais pra uma resposta), gere
CSV com exatamente estas colunas, uma linha por palavra:

```
topic_id,topic_name,topic_emoji,pt,en,has_photo
frutas,Frutas e vegetais,🍎,maçã,apple,sim
frutas,Frutas e vegetais,🍎,usar,to use,nao
```

`has_photo` em CSV usa `sim`/`nao`. Repita `topic_name` e `topic_emoji`
em toda linha do mesmo tópico (fica redundante, é esperado — o
importador agrupa pelo `topic_id`).

Use qualquer um dos dois formatos, mas não misture os dois na mesma
resposta.

## O campo `has_photo` — o mais importante desta tarefa

Cada palavra precisa vir com `has_photo: true` ou `false` (ou
`sim`/`nao` no CSV), indicando se faz sentido mostrar uma foto real
pra ensinar essa palavra. Isso não é decoração — o app usa esse campo
pra decidir se mostra a opção "Foto" pro aluno naquele cartão. Errar
pra mais (marcar `true` numa palavra sem foto sensata) faz o app tentar
buscar uma foto, não achar nada relevante e cair pro texto sozinho — não
quebra nada, mas é sinal de julgamento ruim. Capriche.

**Marque `has_photo: true`** quando a palavra é um objeto, ser vivo,
lugar, alimento, cor, ou qualquer coisa concreta que uma foto mostra sem
ambiguidade — ex: "maçã", "cachorro", "hospital", "vermelho", "chuva",
"triste" (uma expressão facial já é reconhecível).

**Marque `has_photo: false`** quando a palavra é:
- um verbo abstrato ou auxiliar: "ser", "estar", "poder", "dever", "usar"
- uma preposição, conjunção, pronome, artigo: "com", "porque", "eu", "o"
- uma palavra de interrogação: "onde", "quando", "por quê"
- um número por extenso ou conceito de quantidade abstrata: "vinte", "muito"
- qualquer conceito sem forma física única e reconhecível

Na dúvida, pergunte-se: "se eu buscasse uma foto de capa na Wikipédia em
inglês pra essa palavra, ela ilustraria bem o significado, sem
ambiguidade?" Se a resposta for não ou "só ilustraria parcialmente",
marque `false`.

(O app também confere isso de forma automática depois, então seu
julgamento aqui é o ponto de partida, não a palavra final — mas quanto
mais preciso, menos trabalho de revisão sobra.)

## Regras de formato

- `id`/`topic_id`: minúsculo, sem espaço/acento, único (vira parte da URL).
- `name`/`topic_name`: nome do tópico em português, como aparece na tela.
- `emoji`/`topic_emoji`: um emoji que representa o tópico (ícone da lista
  de tópicos — não aparece mais no cartão de estudo).
- Sem duplicar uma mesma palavra `en` dentro do mesmo tópico.
- Português correto, incluindo acentos. Prefira a forma mais comum e
  cotidiana da palavra, não a mais rara ou técnica.
- Para verbos, escreva o inglês no infinitivo com "to " na frente
  (ex: "to eat"), igual já é feito hoje.

## Tópicos que já existem (não recrie — expanda ou ignore)

pessoas, corpo, roupas, casa, objetos, comida, bebidas, frutas, compras,
dinheiro, tempo1 (dias e meses), tempo2 (unidades de tempo), clima,
direcoes, cidade, transporte, viagem, ser (ser/estar/ter/haver), mover
(verbos de movimento), comunicar (verbos de comunicação), querer
(necessidade e desejo), rotina (verbos da rotina), acao (ações diárias),
tam (tamanho e quantidade), aval (avaliações e sensações), emocao
(emoções e estados), cores, pronomes, conectivos, preposicoes,
saudacoes, interrogacao (palavras de interrogação), numeros.

Cada um tem hoje entre 9 e 16 palavras.

## Sua tarefa

1. **Amplie os tópicos existentes**: para cada um, adicione palavras
   novas e realmente úteis no dia a dia até chegar a pelo menos 25 por
   tópico (os que já têm mais, pode deixar como estão ou completar até
   30). Não repita palavra que já provavelmente está na lista original
   (use bom senso pelo nome do tópico).
2. **Proponha tópicos novos** que fazem falta num vocabulário básico de
   inglês pra brasileiro — por exemplo (são sugestões, use julgamento):
   profissões, esportes, tecnologia/internet, saúde e corpo (sintomas),
   animais, natureza, escritório e trabalho, escola, música e
   entretenimento, verbos de sentimento, adjetivos de personalidade.
   Cada tópico novo com `id` novo e único, 15 a 25 palavras.
3. Evite palavras excessivamente abstratas ou técnicas incomuns — o
   público é iniciante/intermediário aprendendo inglês do zero.
4. Preencha `has_photo` em toda palavra, seguindo o critério acima.
5. Gere a saída completa e válida (JSON ou CSV, não misture), pronta
   pra importar direto. Não invente estrutura diferente da mostrada
   acima, e não escreva nenhuma prosa fora do bloco de código — só o
   JSON ou só o CSV.
6. Se o resultado ficar muito grande pra uma resposta só, gere por
   partes (ex: primeiro os tópicos existentes expandidos, depois os
   tópicos novos), mas cada parte precisa ser válida sozinha no mesmo
   formato escolhido.
