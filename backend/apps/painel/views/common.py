from datetime import datetime, time, timedelta
from django.utils import timezone
from apps.delivery.models import OperatingHour, StoreSettings

PERIODS = {
    "hoje": ("Hoje", 0),
    "7d": ("Últimos 7 dias", 6),
    "30d": ("Últimos 30 dias", 29),
}


def period_range(key: str):
    """(start, end, key, label) for a dashboard period, in the store's timezone."""
    key = key if key in PERIODS else "hoje"
    label, days_back = PERIODS[key]
    today = timezone.localdate()
    start = timezone.make_aware(datetime.combine(today - timedelta(days=days_back), time.min))
    end = timezone.make_aware(datetime.combine(today + timedelta(days=1), time.min))
    return start, end, key, label


def store_status(tenant) -> dict:
    """Whether the store is accepting orders right now (same rule the checkout uses)."""
    store = StoreSettings.objects.filter(tenant=tenant).first()
    if store and store.emergency_closed:
        return {"aberta": False, "texto": "Fechada (emergência)", "motivo": store.emergency_closed_reason}

    now = timezone.localtime()
    hours = OperatingHour.objects.filter(tenant=tenant, weekday=(now.weekday() + 1) % 7).first()
    if not hours:
        return {"aberta": True, "texto": "Horário não configurado", "motivo": ""}
    if not hours.is_active:
        return {"aberta": False, "texto": "Fechada hoje", "motivo": ""}
    current = now.strftime("%H:%M")
    if hours.opening_time <= current < hours.closing_time:
        return {"aberta": True, "texto": f"Aberta até {hours.closing_time}", "motivo": ""}
    if current < hours.opening_time:
        return {"aberta": False, "texto": f"Abre às {hours.opening_time}", "motivo": ""}
    return {"aberta": False, "texto": "Encerrada por hoje", "motivo": ""}


def nav_context(request, section: str) -> dict:
    return {"secao": section, "status_loja": store_status(request.tenant)}
