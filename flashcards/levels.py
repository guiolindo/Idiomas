"""
Avaliação de nível baseada no CEFR (Common European Framework of
Reference for Languages) — o padrão internacional pra proficiência em
idiomas. Os limiares aqui usam a estimativa de vocabulário ATIVO
(palavras que a pessoa realmente sabe produzir), que é o que o app
mede via "dominadas" no SRS.

Referências dos limiares de vocabulário (fontes: Cambridge English
Corpus, Council of Europe CEFR descriptors, EF EPI):
    A1 →  0-500 palavras       (turista básico)
    A2 →  500-1000              (situações previsíveis)
    B1 →  1000-2000             (viagens, temas familiares)
    B2 →  2000-4000             (argumenta, entende TV/filmes)
    C1 →  4000-8000             (fluência em contextos complexos)
    C2 →  8000+                 (domínio quase-nativo)

O app hoje tem ~2500 palavras, então o teto realista via este app é
B1/B2. Fica claro na tela — não é um "gamification vazio".
"""


LEVELS = [
    {"code": "A1", "range": (0, 500),      "label": "Iniciante",           "detail": "Vocabulário básico do dia a dia — cumprimentos, comida, família, números."},
    {"code": "A2", "range": (500, 1000),   "label": "Básico",              "detail": "Consegue lidar com situações previsíveis: compras, trabalho simples, rotina."},
    {"code": "B1", "range": (1000, 2000),  "label": "Intermediário",       "detail": "Conversa sobre temas familiares, viagens, planos, opiniões simples."},
    {"code": "B2", "range": (2000, 4000),  "label": "Intermediário sup.",  "detail": "Argumenta, entende TV e filmes sem legenda, textos complexos."},
    {"code": "C1", "range": (4000, 8000),  "label": "Avançado",            "detail": "Fluência em contextos profissionais e acadêmicos, expressões idiomáticas."},
    {"code": "C2", "range": (8000, 999999), "label": "Domínio",            "detail": "Praticamente nativo — nuance, humor, textos técnicos."},
]


def compute_coverage(user, srs_max_level: int) -> dict:
    """Métrica pedagogicamente honesta: cobertura por banda de frequência.

    Substitui o "nível A1 por número de palavras dominadas" (que a revisão
    de SLA chamou de ilusão de progresso — mesma XP do Duolingo).

    Retorna dict com:
      - top500_pct: % das top-500 do inglês real que o aluno domina
      - top500_mastered / top500_total
      - reading_coverage_estimate: estimativa de cobertura textual real
      - level_label: rótulo qualitativo derivado da cobertura das top-500

    Interpretação (Nation 2013):
      - top-500 → ~85% de cobertura de fala informal
      - top-1500 → ~95% de fala + ~85% de escrita
      - top-3000 → ~95% de leitura informal, ~90% escrita
    """
    from .models import Word, Progress
    top500_total = Word.objects.filter(frequency_band=1).count()
    top500_mastered = Progress.objects.filter(
        user=user, word__frequency_band=1, level__gte=srs_max_level,
    ).count()
    top500_pct = round(top500_mastered / top500_total * 100) if top500_total else 0

    # Estimativa GROSSEIRA de cobertura textual: se domina X% das top-500,
    # entende cerca de X% * 0.85 dos tokens de fala informal (Nation 2013).
    # Não é medida científica — só um número honesto pra dar noção.
    reading_coverage_estimate = round(top500_pct * 0.85)

    if top500_pct < 20:
        label = "Início — construindo base"
    elif top500_pct < 50:
        label = "Base parcial"
    elif top500_pct < 80:
        label = "Base sólida das mais frequentes"
    else:
        label = "Base completa das 500 mais frequentes"

    return {
        "top500_pct": top500_pct,
        "top500_mastered": top500_mastered,
        "top500_total": top500_total,
        "reading_coverage_estimate": reading_coverage_estimate,
        "level_label": label,
    }


def compute_level(mastered_count: int) -> dict:
    """Devolve descritor completo do nível atual + progresso pro próximo."""
    mastered_count = max(0, int(mastered_count or 0))
    for i, lvl in enumerate(LEVELS):
        low, high = lvl["range"]
        if mastered_count < high:
            span = high - low
            within = mastered_count - low
            progress_pct = round(within / span * 100) if span else 100
            next_lvl = LEVELS[i + 1] if i + 1 < len(LEVELS) else None
            return {
                "code": lvl["code"],
                "label": lvl["label"],
                "detail": lvl["detail"],
                "mastered": mastered_count,
                "level_min": low,
                "level_max": high,
                "within_level": within,
                "span": span,
                "progress_pct": max(0, min(100, progress_pct)),
                "next_code": next_lvl["code"] if next_lvl else None,
                "to_next": max(0, high - mastered_count),
            }
    # nunca deve chegar aqui (C2 range vai até 999999)
    lvl = LEVELS[-1]
    return {
        "code": lvl["code"], "label": lvl["label"], "detail": lvl["detail"],
        "mastered": mastered_count, "level_min": lvl["range"][0], "level_max": lvl["range"][1],
        "within_level": mastered_count - lvl["range"][0], "span": 1,
        "progress_pct": 100, "next_code": None, "to_next": 0,
    }
