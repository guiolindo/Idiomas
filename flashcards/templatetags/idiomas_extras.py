"""Filtros de template pequenos e específicos deste app."""
from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def quando(dt):
    """Devolve uma versão humana curta de uma data:
    - futuras: "hoje", "amanhã", "em 3 dias", "em 2 semanas"
    - passadas: "agora mesmo", "há 5 min", "há 2h", "há 3 dias"
    """
    if not dt:
        return ""
    now = timezone.now()
    delta = dt - now
    total = delta.total_seconds()
    if total <= 0:
        # passado
        ago = -total
        if ago < 60:
            return "agora mesmo"
        if ago < 3600:
            return f"há {int(ago // 60)} min"
        if ago < 86400:
            return f"há {int(ago // 3600)}h"
        days = int(ago // 86400)
        if days == 1:
            return "ontem"
        if days < 7:
            return f"há {days} dias"
        if days < 30:
            return f"há {days // 7} semana{'s' if days // 7 > 1 else ''}"
        return f"há {days // 30} {'mês' if days // 30 == 1 else 'meses'}"
    days = delta.days
    if days == 0:
        return "hoje"
    if days == 1:
        return "amanhã"
    if days < 7:
        return f"em {days} dias"
    if days < 14:
        return "em 1 semana"
    if days < 30:
        weeks = days // 7
        return f"em {weeks} semanas"
    if days < 60:
        return "em 1 mês"
    months = days // 30
    return f"em {months} meses"
