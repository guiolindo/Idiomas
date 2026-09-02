"""Filtros de template pequenos e específicos deste app."""
from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def quando(dt):
    """Devolve uma versão humana curta de uma data futura:
    "hoje", "amanhã", "em 3 dias", "em 2 semanas", etc.
    Se a data já passou, devolve "vencido".
    """
    if not dt:
        return ""
    now = timezone.now()
    delta = dt - now
    days = delta.days
    if delta.total_seconds() <= 0:
        return "vencido"
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
