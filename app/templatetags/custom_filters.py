from django import template

register = template.Library()

@register.filter
def lookup(dictionary, key):
    """
    Template filter to lookup a dictionary value by key.
    Usage: {{ my_dict|lookup:key_var }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)

@register.filter
def subtract(value, arg):
    """
    Template filter to subtract arg from value.
    Usage: {{ value|subtract:arg }}
    """
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0
