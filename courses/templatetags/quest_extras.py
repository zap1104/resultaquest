import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name='structured')
def structured(value):
    """Turns plain-text review content into real HTML structure:
    lines starting with '- ' or '• ' become <ul> items, lines starting
    with '1.' / '2.' etc become <ol> items, everything else becomes a
    paragraph. This is intentionally simple (not a full markdown parser)
    — it only recognizes the patterns Gemini's prompt is likely to
    produce for a "study guide" style response.
    """
    if not value:
        return ''

    lines = value.strip().split('\n')
    html_parts = []
    list_buffer = []
    list_type = None  # 'ul' or 'ol'

    def flush_list():
        if list_buffer and list_type:
            items = ''.join(f'<li>{item}</li>' for item in list_buffer)
            html_parts.append(f'<{list_type}>{items}</{list_type}>')
            list_buffer.clear()

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            flush_list()
            continue

        bullet_match = re.match(r'^[-•]\s+(.*)', line)
        numbered_match = re.match(r'^\d+[.)]\s+(.*)', line)

        if bullet_match:
            if list_type != 'ul':
                flush_list()
                list_type = 'ul'
            list_buffer.append(escape(bullet_match.group(1)))
        elif numbered_match:
            if list_type != 'ol':
                flush_list()
                list_type = 'ol'
            list_buffer.append(escape(numbered_match.group(1)))
        else:
            flush_list()
            list_type = None
            html_parts.append(f'<p>{escape(line)}</p>')

    flush_list()
    return mark_safe(''.join(html_parts))