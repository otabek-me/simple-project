from django import template
from decimal import Decimal

register = template.Library()


@register.filter
def format_price(value):
    """Format price with thousands separator and 2 decimal places."""
    try:
        if isinstance(value, str):
            value = value.replace(' ', '')
        value = Decimal(str(value))
        integer_part = int(value)
        formatted = f"{integer_part:,}".replace(',', ' ')
        decimal_part = value - int(value)
        if decimal_part > 0:
            formatted += f".{int(decimal_part * 100):02d}"
        else:
            formatted += '.00'
        return formatted
    except (ValueError, TypeError, Exception):
        return str(value)