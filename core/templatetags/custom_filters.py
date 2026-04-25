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
