from django import template

register = template.Library()


@register.filter
def format_price(value):
    """Format price with thousands separator and 2 decimal places."""
    try:
        value = float(value)
        return f"{value:,.2f}".replace(',', ' ')
    except (ValueError, TypeError):
        return value
