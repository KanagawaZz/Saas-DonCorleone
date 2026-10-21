from decimal import Decimal, InvalidOperation
from urllib.parse import quote
from django import template
from django.conf import settings
from django.utils import timezone

register = template.Library()

STATUS_TONES = {
    "NOVO": "novo",
    "CONFIRMADO": "preparo",
    "PREPARO": "preparo",
    "SAIU_PARA_ENTREGA": "rota",
    "PRONTO_RETIRADA": "rota",
    "CONCLUIDO": "concluido",
    "CANCELADO": "cancelado",
}

STATUS_SHORT = {
    "NOVO": "Pendente",
    "CONFIRMADO": "Em preparo",
    "PREPARO": "Em preparo",
    "SAIU_PARA_ENTREGA": "Enviado",
    "PRONTO_RETIRADA": "Pronto p/ retirada",
    "CONCLUIDO": "Concluído",
    "CANCELADO": "Cancelado",
}


@register.filter
def brl(value):
    """12345.5 -> 'R$ 12.345,50'"""
    if value in (None, ""):
        return "—"
    try:
        number = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return value
    integer, cents = f"{abs(number):.2f}".split(".")
    integer = f"{int(integer):,}".replace(",", ".")
    return f"{'-' if number < 0 else ''}R$ {integer},{cents}"


@register.filter
def foto_url(product):
    """Uploaded image, or the site's photo path made absolute with SITE_PUBLIC_URL."""
    if product.image:
        return product.image.url
    path = product.photo_url or ""
    if not path or path.startswith(("http://", "https://")):
        return path
    return f"{settings.SITE_PUBLIC_URL}/{path.lstrip('/')}"


@register.filter
def status_tone(status):
    return STATUS_TONES.get(status, "neutro")


@register.filter
def status_short(status):
    return STATUS_SHORT.get(status, status)


@register.filter
def tempo_desde(value):
    """Elapsed time in short Portuguese: 'agora', 'há 7 min', 'há 1 h 20 min', 'há 3 dias'."""
    if not value:
        return ""
    minutes = int((timezone.now() - value).total_seconds() // 60)
    if minutes < 1:
        return "agora"
    if minutes < 60:
        return f"há {minutes} min"
    hours, rest = divmod(minutes, 60)
    if hours < 24:
        return f"há {hours} h {rest} min" if rest else f"há {hours} h"
    days = hours // 24
    return f"há {days} dia{'s' if days > 1 else ''}"


@register.filter
def minutos_desde(value):
    if not value:
        return 0
    return int((timezone.now() - value).total_seconds() // 60)


@register.filter
def telefone(value):
    """65999990000 -> (65) 99999-0000"""
    digits = "".join(filter(str.isdigit, value or ""))
    if digits.startswith("55") and len(digits) in (12, 13):
        digits = digits[2:]
    if len(digits) == 11:
        return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
    if len(digits) == 10:
        return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
    return value


@register.filter
def whatsapp_link(value):
    digits = "".join(filter(str.isdigit, value or ""))
    if digits and not digits.startswith("55"):
        digits = f"55{digits}"
    return f"https://wa.me/{digits}"


def _destination(order) -> str:
    """Address in the form navigation apps understand best."""
    street = ", ".join(p for p in [order.delivery_street, order.delivery_number] if p)
    city = f"{order.delivery_city} - MT" if order.delivery_city else ""
    return ", ".join(p for p in [street, order.delivery_neighborhood, city] if p)


@register.filter
def link_google_maps(order):
    return f"https://www.google.com/maps/dir/?api=1&travelmode=driving&destination={quote(_destination(order))}"


@register.filter
def link_waze(order):
    return f"https://waze.com/ul?navigate=yes&q={quote(_destination(order))}"


@register.simple_tag(takes_context=True)
def query_com(context, **params):
    """Current querystring with some parameters replaced (used by filters and pagination)."""
    query = context["request"].GET.copy()
    for key, value in params.items():
        if value in (None, ""):
            query.pop(key, None)
        else:
            query[key] = value
    encoded = query.urlencode()
    return f"?{encoded}" if encoded else "?"
