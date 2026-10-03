from django import template
from infotech.i18n import text
register = template.Library()
@register.simple_tag(takes_context=True)
def t(context, value):
    return text(str(value), context['request'].session.get('infotech_language', 'zh'))

