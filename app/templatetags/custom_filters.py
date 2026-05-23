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
def get_course_certificate(certificates, course_id):
    """
    Get certificate for a specific course from a list of certificates.
    Usage: {{ enrollment.registration.certificates.all|get_course_certificate:enrollment.course.id }}
    """
    if not certificates:
        return None
    for cert in certificates:
        if cert.certificate_type == 'COURSE' and cert.course_id == course_id:
            return cert
    return None

