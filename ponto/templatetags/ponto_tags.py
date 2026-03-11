from django import template
from ponto.utils import format_minutos_hhmm

register = template.Library()

@register.filter
def format_minutos(val):
    try:
        return format_minutos_hhmm(int(val))
    except (ValueError, TypeError):
        return "00:00"

@register.filter
def multiply(value, arg):
    try:
        return int(value) * int(arg)
    except (ValueError, TypeError):
        return 0
