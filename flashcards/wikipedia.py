"""
Busca a foto de capa do artigo da Wikipedia sobre uma palavra em inglês.

Usamos a API de resumo da Wikipedia (não a busca da Wikimedia Commons) de
propósito: ela devolve UM artigo já desambiguado por palavra (então "apple"
cai na fruta, não em qualquer coisa que combine com o texto), e a ausência
de "thumbnail" é justamente o sinal que usamos pra saber que a palavra não
tem uma foto que faça sentido (verbos, preposições, conceitos abstratos
viram artigos de desambiguação ou não têm imagem de capa). A busca da
Commons também vinha sendo bloqueada pela política antibot da Wikimedia
sob volume de tráfego de app.
"""
import httpx

HEADERS = {
    "User-Agent": "CadernoDeIdiomas/1.0 (app pessoal de flashcards; contato: brzueira342386@gmail.com)"
}


def fetch_summary(q: str) -> dict:
    """{'found': False} ou {'found': True, 'url', 'page', 'title'}"""
    title = q.strip().replace(" ", "_")
    if not title:
        return {"found": False}
    try:
        resp = httpx.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}",
            headers=HEADERS, timeout=8, follow_redirects=True,
        )
    except httpx.HTTPError:
        return {"found": False}

    if resp.status_code != 200:
        return {"found": False}

    data = resp.json()
    thumb = data.get("thumbnail")
    # "disambiguation" = página de lista de sentidos (ex: "use" -> vários
    # significados), não uma imagem específica da palavra.
    if thumb and data.get("type") != "disambiguation":
        return {
            "found": True,
            "url": thumb["source"],
            "page": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
            "title": data.get("title", q),
        }
    return {"found": False}
