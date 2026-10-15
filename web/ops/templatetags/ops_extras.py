from django import template

register = template.Library()


@register.filter
def dur(seconds):
    """초 → '12분 3초' 형식."""
    if seconds in (None, ""):
        return "-"
    s = int(round(float(seconds)))
    if s < 60:
        return f"{s}초"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m}분 {s}초"
    h, m = divmod(m, 60)
    return f"{h}시간 {m}분"


@register.filter
def num(value):
    if value in (None, ""):
        return "-"
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return value
