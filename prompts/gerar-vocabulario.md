Você vai gerar um vocabulário grande de português → inglês para um app de flashcards, em JSON pronto pra importar.

## Formato de saída (obrigatório)

```json
{
  "topics": [
    {
      "id": "profissoes",
      "name": "Profissões",
      "emoji": "💼",
      "words": [
        {"pt": "médico", "en": "doctor", "has_photo": true},
        {"pt": "advogado", "en": "lawyer", "has_photo": false}
      ]
    }
  ]
}
```

Regras de formato:
- `id`: exatamente o slug que aparece na lista de tópicos abaixo (minúsculo, sem espaço/acento).
- `name`/`emoji`: exatamente como na lista abaixo.
- `pt`: português correto, com acentos. `en`: inglês em minúsculo (exceto nomes próprios). Verbos no infinitivo com "to " na frente (ex: "to download").
- `has_photo`: `true` **somente** se a palavra for um objeto, ser vivo ou lugar concreto, fotografável sem ambiguidade (ex: "cachorro"→"dog" é `true`; "gentil"→"kind" é `false`; "baixar"→"to download" é `false`). Na dúvida, marque `false` — é melhor esconder a opção de foto do que mostrar uma foto errada.
- Não repita a mesma palavra `en` duas vezes, nem dentro do mesmo tópico nem em tópicos diferentes.
- Responda **apenas** o JSON. Sem markdown, sem crase, sem explicação antes ou depois.

## Regra mais importante: fique estritamente dentro do tema

Cada tópico abaixo tem uma **definição** e 3 **exemplos-âncora** (que você NÃO deve repetir, são só pra ancorar o assunto). Gere palavras que pertençam estritamente a essa definição — nada de misturar objetos genéricos, cores, ou palavras de outros temas só para variar. Um teste real com um modelo menor mostrou exatamente esse erro: pedido "profissões", ele devolveu "carro", "piano", "cozinha" — errado. Não repita esse erro. Se não tiver certeza que uma palavra pertence ao tema, não inclua.

## Tópicos para gerar (60 no total — gere todos, ou em lotes se precisar)

Formato de cada linha: `id | nome | emoji | quantidade | definição | âncoras (não repetir)`

```
profissoes | Profissões | 💼 | 22 | nomes de profissões e ocupações (o que uma pessoa faz para trabalhar) | médico=doctor, professor=teacher, engenheiro=engineer
escritorio | Material de escritório | 🖇 | 18 | objetos usados numa mesa de escritório | grampeador=stapler, clipe de papel=paperclip, pasta=folder
escola | Escola | 🏫 | 20 | objetos e conceitos do dia a dia escolar | quadro=whiteboard, giz=chalk, borracha=eraser
internet | Internet e redes sociais | 📶 | 20 | palavras usadas online e em redes sociais | senha=password, aplicativo=app, curtir=to like
eletronicos | Aparelhos eletrônicos | 🔌 | 18 | eletrodomésticos e aparelhos elétricos da casa | geladeira=refrigerator, micro-ondas=microwave, aspirador de pó=vacuum cleaner
moveis | Móveis | 🛋 | 18 | móveis de dentro de uma casa | sofá=sofa, armário=wardrobe, estante=bookshelf
cozinha_utensilios | Utensílios de cozinha | 🍳 | 20 | utensílios e ferramentas usados para cozinhar | panela=pot, faca=knife, garfo=fork
banheiro | Itens de banheiro | 🛁 | 16 | objetos que ficam num banheiro | sabonete=soap, escova de dente=toothbrush, chuveiro=shower
jardim | Jardim e plantas | 🌻 | 18 | plantas e elementos de um jardim (não use a palavra "garden") | árvore=tree, flor=flower, grama=grass
animais_domesticos | Animais domésticos | 🐶 | 14 | animais de estimação comuns | cachorro=dog, gato=cat, peixe=fish
animais_fazenda | Animais de fazenda | 🐄 | 14 | animais criados numa fazenda | vaca=cow, porco=pig, galinha=chicken
animais_selvagens | Animais selvagens | 🦁 | 22 | animais selvagens conhecidos | leão=lion, elefante=elephant, urso=bear
aves | Aves e pássaros | 🦅 | 14 | tipos de aves e pássaros | pássaro=bird, águia=eagle, pinguim=penguin
insetos | Insetos | 🐝 | 14 | tipos de insetos | formiga=ant, abelha=bee, borboleta=butterfly
mar_vida | Vida marinha | 🐋 | 16 | animais que vivem no mar | baleia=whale, golfinho=dolphin, tubarão=shark
corpo_avancado | Partes do corpo (avançado) | 🫁 | 16 | partes internas ou avançadas do corpo, sem repetir cabeça/olho/mão/braço/perna/pé/coração/costas/barriga | fígado=liver, pulmão=lung, músculo=muscle
saude_sintomas | Sintomas de saúde | 🤒 | 16 | sintomas e sensações de estar doente | febre=fever, tosse=cough, dor de cabeça=headache
hospital_itens | No hospital | 🏥 | 16 | objetos e conceitos de hospital e tratamento médico | remédio=medicine, seringa=syringe, vacina=vaccine
esportes | Esportes | ⚽ | 20 | nomes de esportes | futebol=soccer, basquete=basketball, natação=swimming
exercicio | Exercício físico | 🏋 | 14 | palavras de academia e exercício físico | academia=gym, corrida=running, ioga=yoga
instrumentos_musicais | Instrumentos musicais | 🎸 | 16 | instrumentos musicais | violão=guitar, piano=piano, bateria=drums
musica_termos | Música | 🎵 | 14 | palavras sobre música, sem repetir instrumentos | canção=song, banda=band, show=concert
filmes_tv | Filmes e TV | 🎬 | 16 | palavras sobre cinema e televisão | filme=movie, ator=actor, seriado=TV series
arte | Arte | 🎨 | 14 | palavras sobre artes visuais | pintura=painting, escultura=sculpture, desenho=drawing
literatura | Literatura | 📚 | 14 | palavras sobre livros e literatura | romance=novel, poema=poem, autor=author
jogos | Jogos | 🎲 | 14 | jogos de tabuleiro, cartas e passatempos | jogo de tabuleiro=board game, quebra-cabeça=puzzle, dado=dice
brinquedos | Brinquedos | 🧸 | 14 | brinquedos de criança | boneca=doll, bola=ball, pipa=kite
festa | Festa e celebração | 🎉 | 16 | palavras sobre festas e comemorações | aniversário=birthday, presente=gift, balão=balloon
feriados | Feriados | 🎄 | 10 | feriados e datas comemorativas conhecidas | natal=Christmas, ano novo=New Year, páscoa=Easter
casamento | Casamento | 💍 | 12 | palavras sobre casamento | noiva=bride, noivo=groom, aliança=wedding ring
governo | Governo e política básica | 🏛 | 16 | conceitos básicos de governo e política, vocabulário neutro | presidente=president, lei=law, eleição=election
lei_ordem | Lei e ordem | 👮 | 14 | vocabulário sobre polícia e justiça | polícia=police, prisão=prison, juiz=judge
financas_avancado | Finanças | 📈 | 14 | conceitos financeiros avançados, sem repetir dinheiro/cartão/banco/conta/pagar/custo/barato/caro/troco/salário | investimento=investment, empréstimo=loan, imposto=tax
compras_online | Compras online | 🛍 | 12 | vocabulário de compras pela internet | carrinho=cart, entrega=delivery, frete=shipping
restaurante | No restaurante | 🍽 | 14 | vocabulário de restaurante, sem repetir mesa/conta/comida em geral | cardápio=menu, garçom=waiter, gorjeta=tip
hotel | Hotel e hospedagem | 🏨 | 12 | vocabulário de hotel, sem repetir quarto/chave/reserva | recepção=reception, hóspede=guest, diária=nightly rate
aeroporto | Aeroporto | 🛫 | 12 | vocabulário de aeroporto, sem repetir passaporte/mala/bilhete/embarque/voo | pista=runway, piloto=pilot, comissário de bordo=flight attendant
carro_partes | Partes do carro | 🚘 | 14 | peças de um carro | pneu=tire, motor=engine, volante=steering wheel
transito | Trânsito | 🚦 | 12 | vocabulário de trânsito e ruas | semáforo=traffic light, pedágio=toll, engarrafamento=traffic jam
natureza | Natureza | 🏞 | 18 | acidentes geográficos e elementos da natureza | montanha=mountain, rio=river, floresta=forest
clima_fenomeno | Fenômenos climáticos | 🌪 | 10 | fenômenos climáticos extremos, sem repetir chuva/sol/vento/neve | furacão=hurricane, terremoto=earthquake, tsunami=tsunami
meio_ambiente | Meio ambiente | ♻️ | 14 | vocabulário de meio ambiente e sustentabilidade | poluição=pollution, reciclagem=recycling, lixo=trash
geografia | Geografia | 🌍 | 14 | conceitos gerais de geografia, não nomes de países específicos | país=country, continente=continent, oceano=ocean
nacionalidades | Nacionalidades | 🌐 | 16 | nacionalidades de pessoas de países conhecidos | brasileiro=Brazilian, americano=American, japonês=Japanese
idiomas | Idiomas | 🗣 | 12 | nomes de idiomas falados no mundo | português=Portuguese, inglês=English, espanhol=Spanish
formas | Formas geométricas | 🔺 | 10 | formas geométricas básicas | círculo=circle, quadrado=square, triângulo=triangle
materiais | Materiais | 🪵 | 12 | materiais de que objetos são feitos | madeira=wood, metal=metal, plástico=plastic
ferramentas | Ferramentas | 🔨 | 14 | ferramentas manuais de trabalho | martelo=hammer, chave de fenda=screwdriver, serra=saw
construcao | Construção | 🧱 | 12 | vocabulário de construção civil | tijolo=brick, cimento=cement, andaime=scaffolding
eletricidade | Eletricidade | 💡 | 10 | vocabulário básico de eletricidade doméstica | tomada=outlet, fio=wire, lâmpada=light bulb
personalidade | Personalidade | 🧠 | 20 | adjetivos de personalidade, sem repetir bom/ruim/feliz/triste | gentil=kind, teimoso=stubborn, engraçado=funny
aparencia_fisica | Aparência física | 🧑 | 12 | aparência física de uma pessoa, sem repetir alto/baixo | careca=bald, barba=beard, bigode=mustache
familia_extensa | Família estendida | 👪 | 10 | parentes além de pai/mãe/irmão/irmã/avô/avó/tio/tia | primo=cousin, sobrinho=nephew, sogra=mother-in-law
bebe_criancas | Bebê e crianças | 👶 | 10 | itens usados para cuidar de bebês | fralda=diaper, mamadeira=baby bottle, carrinho de bebê=stroller
idosos | Terceira idade | 🧓 | 8 | vocabulário respeitoso sobre pessoas idosas | aposentadoria=retirement, bengala=cane, idoso=elderly person
emergencia | Emergência | 🚨 | 12 | vocabulário de situações de emergência | incêndio=fire, ambulância=ambulance, socorro=help
seguranca | Segurança | 🔒 | 10 | vocabulário de segurança doméstica, sem repetir câmera | guarda=security guard, fechadura=lock, extintor de incêndio=fire extinguisher
tecnologia_verbos | Verbos de tecnologia | ⌨️ | 14 | verbos usados com computadores e celulares | baixar=to download, enviar=to send, imprimir=to print
cozinha_verbos | Verbos de cozinhar | 🍳 | 12 | verbos de técnicas de cozinhar, sem repetir comer/beber/cozinhar | fritar=to fry, assar=to bake, ferver=to boil
```

## Se o resultado for muito grande

Gere por lotes (ex: 15 tópicos por resposta), sempre no mesmo formato JSON válido, até cobrir os 60. Cada lote precisa ser um JSON `{"topics": [...]}` válido sozinho — nunca prosa fora do JSON.

Meta total: ~1300 palavras novas, coerentes e realmente úteis para quem está aprendendo inglês do zero/básico-intermediário.
