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

@register.filter
def startDate(input: str): 
    """
    Template filter to convert a string in the format 'YYYY-MM-DD' to a date object.
    Usage: {{ input|startDate }}
    """
    from datetime import date
    year = input[:4]
    week = input[5:7]
    try:
        return date.fromisocalendar(int(year), int(week), 1)
    except (ValueError, TypeError):
        return None

@register.filter
def endDate(input: str): 
    """
    Template filter to convert a string in the format 'YYYY-MM-DD' to a date object.
    Usage: {{ input|endDate }}
    """
    from datetime import date
    year = input[:4]
    week = input[5:7]
    try:
        return date.fromisocalendar(int(year), int(week), 7)
    except (ValueError, TypeError):
        return None