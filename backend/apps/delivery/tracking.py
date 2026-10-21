"""
Courier live location: when a position may be recorded and how it is stored.
Positions come from Traccar Client (form POST with id, lat, lon, timestamp, accuracy, batt).
"""
import math
from datetime import datetime, timedelta, timezone as dt_timezone
from urllib.parse import urlencode
from django.utils import timezone
from .models import CourierLocation, Employee, OperatingHour, StoreSettings

# Couriers may arrive a little before opening and are still delivering after closing
BEFORE_OPENING = timedelta(minutes=30)
AFTER_CLOSING = timedelta(minutes=60)
# Positions older than this when they arrive (buffered while offline) are discarded
MAX_AGE = timedelta(minutes=15)
# Traccar barely sends while the phone is still, so the last position stays on the map this long
SHOW_LAST_POSITION_FOR = timedelta(hours=6)
# Without a new position for this long, the courier is shown as stopped
STOPPED_AFTER = timedelta(minutes=10)


# Traccar Client settings applied by the QR code / config link (keys as the app reads them)
TRACCAR_SETTINGS = {
    "accuracy": "high",
    "distance": "50",
    "interval": "120",
    "buffer": "true",
    "stop_detection": "true",
}
TRACCAR_START_LINK = "org.traccar.client://action/start"
TRACCAR_STOP_LINK = "org.traccar.client://action/stop"


def traccar_links(server_url: str, token: str) -> dict:
    """
    QR code for the Traccar settings scanner: an http(s) URL whose origin + path becomes the
    server URL and whose query sets the rest. The config link opens the app and asks to apply.
    """
    params = {"id": token, **TRACCAR_SETTINGS}
    return {
        "traccar_url": server_url,
        "traccar_qr": f"{server_url}?{urlencode(params)}",
        "traccar_config_link": f"org.traccar.client://config?{urlencode({'url': server_url, **params})}",
        "traccar_start_link": TRACCAR_START_LINK,
        "traccar_stop_link": TRACCAR_STOP_LINK,
    }


def _at_today(hhmm: str) -> datetime:
    hour, minute = map(int, hhmm.split(":"))
    return timezone.localtime().replace(hour=hour, minute=minute, second=0, microsecond=0)


def within_store_hours(tenant) -> bool:
    """Today's opening hours with a margin on both ends; closed days and emergency closing count as closed."""
    store = StoreSettings.objects.filter(tenant=tenant).first()
    if store and store.emergency_closed:
        return False
    now = timezone.localtime()
    hours = OperatingHour.objects.filter(tenant=tenant, weekday=(now.weekday() + 1) % 7, is_active=True).first()
    if not hours:
        return False
    try:
        return _at_today(hours.opening_time) - BEFORE_OPENING <= now <= _at_today(hours.closing_time) + AFTER_CLOSING
    except ValueError:
        return False


def tracking_allowed(courier: Employee) -> bool:
    """
    Privacy rule: only while the courier is on duty today and either the store is open
    or they still have an order in the bag.
    """
    from apps.orders.models import Order  # orders depends on delivery

    if not (courier.is_active and courier.role == Employee.Role.COURIER and courier.is_working_today):
        return False
    if courier.orders.filter(status=Order.Status.SAIU_PARA_ENTREGA).exists():
        return True
    return within_store_hours(courier.tenant)


def _number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _timestamp(value):
    """Traccar sends Unix seconds; milliseconds are accepted too. Falls back to now."""
    number = _number(value)
    now = timezone.now()
    if number is None:
        return now
    if number > 1e11:
        number /= 1000
    try:
        moment = datetime.fromtimestamp(number, tz=dt_timezone.utc)
    except (OverflowError, OSError, ValueError):
        return now
    return min(moment, now)  # phone clocks running ahead never place a position in the future


def record_position(data) -> str:
    """
    Stores the courier's position if allowed. Returns the outcome for logging only:
    the HTTP answer is always 200, because Traccar retries a rejected position forever
    and stops sending newer ones until it goes through.
    """
    token = (data.get("id") or data.get("deviceid") or "").strip()
    courier = Employee.objects.filter(access_token=token).select_related("tenant").first() if token else None
    if not courier:
        return "código desconhecido"
    if not tracking_allowed(courier):
        return "fora do serviço"

    lat, lon = _number(data.get("lat")), _number(data.get("lon"))
    if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0):
        return "coordenada inválida"
    recorded_at = _timestamp(data.get("timestamp"))
    if timezone.now() - recorded_at > MAX_AGE:
        return "posição antiga"
    current = CourierLocation.objects.filter(courier=courier).first()
    if current and current.recorded_at >= recorded_at:
        return "posição fora de ordem"

    battery = _number(data.get("batt"))
    accuracy = _number(data.get("accuracy"))
    CourierLocation.objects.update_or_create(courier=courier, defaults={
        "latitude": round(lat, 6),
        "longitude": round(lon, 6),
        "accuracy": accuracy if accuracy and accuracy > 0 else None,
        "battery": int(max(0, min(100, battery))) if battery is not None else None,
        "recorded_at": recorded_at,
    })
    if not courier.traccar_connected_at:
        Employee.objects.filter(pk=courier.pk).update(traccar_connected_at=timezone.now())
    return "ok"


def end_shift(courier: Employee) -> None:
    """Courier is off: forget where they were."""
    CourierLocation.objects.filter(courier=courier).delete()
