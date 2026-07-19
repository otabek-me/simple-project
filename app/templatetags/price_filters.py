from django import template
from decimal import Decimal, ROUND_DOWN

register = template.Library()


@register.filter
def format_price(value):
    """Format price with thousands separator and 2 decimal places."""
    try:
        if isinstance(value, str):
            value = value.replace(' ', '')
        value = Decimal(str(value))
        integer_part = int(value // 1)
        formatted = f"{integer_part:,}".replace(',', ' ')
        decimal_part = int((value % 1) * 100)
        formatted += f".{decimal_part:02d}"
        return formatted
    except (ValueError, TypeError, Exception):
        return str(value)