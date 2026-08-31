Você vai expandir o banco de vocabulário de um app de flashcards português → inglês, gerando um arquivo JSON pronto pra importar.

## Formato exato de saída

```json
{
  "topics": [
    {
      "id": "frutas",
      "name": "Frutas e vegetais",
      "emoji": "🍎",
      "words": [
        {"pt": "maçã", "en": "apple"},
        {"pt": "banana", "en": "banana"}
      ]
    }
  ]
}
```

Regras de formato:
- `id`: minúsculo, sem espaço/acento, único (vira parte da URL).
- `name`: nome do tópico em português, como aparece na tela.
- `emoji`: um emoji que representa o tópico (usado só como ícone do
  tópico na lista — não é mais usado no cartão de estudo).
- `words`: cada palavra com `pt` (português) e `en` (inglês). Não inclua
  campo de emoji por palavra — não é mais usado.
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
4. Gere o JSON completo e válido, pronto pra colar direto num arquivo
   `words.json`. Não invente estrutura diferente da mostrada acima.
5. Se o resultado ficar muito grande pra uma resposta só, gere por
   partes (ex: primeiro os tópicos existentes expandidos, depois os
   tópicos novos), mas cada parte precisa ser um JSON válido no mesmo
   formato — nunca prosa fora do JSON.
