from django import template

register = template.Library()

@register.filter
def split(value, arg):
    return value.split(arg)

@register.filter
def in_list(value, arg):
    return value in arg.split(',')