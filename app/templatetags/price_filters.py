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
        # Use string representation to avoid rounding issues
        s = f"{value:.2f}"
        parts = s.split('.')
        int_part = int(parts[0])
        formatted = f"{int_part:,}".replace(',', ' ')
        return f"{formatted}.{parts[1]}"
    except (ValueError, TypeError, Exception):
        return str(value)