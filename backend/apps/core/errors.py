"""
Unexpected errors: every failure gets an occurrence code (ERR-DDMM-XXXX) shown to the user,
and the full context is kept for support (database, structured log line and a WhatsApp alert).
"""
import hashlib
import json
import logging
import random
import re
import secrets
import threading
import traceback
from datetime import timedelta
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger("doncorleone.errors")

CODE_CHARSET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"  # no 0/O, 1/I/L: easy to read over the phone
SENSITIVE_KEY = re.compile(r"pass|senha|token|secret|csrf|key|authorization|cookie|session|cvv|card|cartao", re.I)
MAX_VALUE_CHARS = 2000
RETENTION = timedelta(days=30)
ALERT_INTERVAL = 60 * 30  # same error signature alerts at most once every 30 min


def new_code() -> str:
    now = timezone.localtime()
    return f"ERR-{now:%d%m}-{''.join(secrets.choice(CODE_CHARSET) for _ in range(4))}"


def area_for(path: str) -> str:
    """Which part of the system the request belongs to (decides the error page and message)."""
    if path.startswith("/api/"):
        return "api"
    if path.startswith(("/painel/", "/admin/")):
        return "painel"
    if path.startswith("/entregador/"):
        return "entregador"
    return "geral"


def _clean(value, depth=0):
    """Request data with secrets removed and long values cut."""
    if depth > 5:
        return "…"
    if isinstance(value, dict):
        return {k: "[removido]" if SENSITIVE_KEY.search(str(k)) else _clean(v, depth + 1) for k, v in value.items()}
    if isinstance(value, list):
        return [_clean(v, depth + 1) for v in value[:50]]
    if isinstance(value, str) and len(value) > MAX_VALUE_CHARS:
        return value[:MAX_VALUE_CHARS] + "…"
    return value


def capture_body(request) -> None:
    """
    Keeps a copy of small JSON/form bodies before the view reads them (DRF consumes the stream,
    after which request.body is no longer available).
    """
    content_type = request.META.get("CONTENT_TYPE", "")
    try:
        length = int(request.META.get("CONTENT_LENGTH") or 0)
    except ValueError:
        length = 0
    if request.method in ("POST", "PUT", "PATCH") and 0 < length <= 100_000 and \
            content_type.startswith(("application/json", "application/x-www-form-urlencoded")):
        try:
            request._error_body = request.body
        except Exception:  # never break the request because of error tracking
            pass


def request_data(request) -> dict:
    data = {"query": _clean(request.GET.dict())}
    body = getattr(request, "_error_body", None)
    if body:
        text = body.decode("utf-8", "replace")
        if request.META.get("CONTENT_TYPE", "").startswith("application/json"):
            try:
                data["body"] = _clean(json.loads(text))
            except ValueError:
                data["body"] = _clean(text)
        else:
            from django.http import QueryDict
            data["body"] = _clean(QueryDict(text).dict())
    files = getattr(request, "_files", None)
    if files:
        data["files"] = [f"{name}: {f.name} ({f.size} bytes)" for name, f in files.items()]
    return data


def _origin(exc) -> str:
    """Last line of our own code in the traceback (where to look first), not of Django or a library."""
    frames = traceback.extract_tb(exc.__traceback__)
    base = str(settings.BASE_DIR)
    ours = [f for f in frames if f.filename.startswith(base) and "site-packages" not in f.filename]
    frame = (ours or frames or [None])[-1]
    if not frame:
        return ""
    return f"{frame.filename.removeprefix(base).lstrip('/\\')}:{frame.lineno} ({frame.name})"


def _client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR", ""))[:45]


def record(request, exc, code: str):
    """Saves the occurrence (log line first: it works even when the database is the problem)."""
    from .models import ErrorEvent

    user = getattr(request, "user", None)
    authenticated = bool(user and user.is_authenticated)
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    origin = _origin(exc)
    event = {
        "code": code,
        "occurred_at": timezone.now().isoformat(),
        "area": area_for(request.path),
        "method": request.method,
        "path": request.get_full_path()[:500],
        "exception": f"{type(exc).__module__}.{type(exc).__qualname__}",
        "message": str(exc)[:500],
        "origin": origin,
        "user_id": str(user.pk) if authenticated else None,
        "user": user.get_username() if authenticated else "",
        "ip": _client_ip(request),
        "data": request_data(request),
    }
    logger.error(json.dumps({**event, "traceback": tb}, ensure_ascii=False, default=str))

    try:
        ErrorEvent.objects.create(
            code=code, area=event["area"], method=event["method"], path=event["path"],
            exception_type=event["exception"], message=event["message"], origin=origin, traceback=tb,
            user=user if authenticated else None, user_label=event["user"], ip=event["ip"],
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:300], request_data=event["data"],
        )
        if random.random() < 0.02:
            ErrorEvent.objects.filter(occurred_at__lt=timezone.now() - RETENTION).delete()
    except Exception:
        logger.exception("[Ocorrência %s] não foi possível gravar no banco", code)

    _alert_support(request, event)


def _alert_support(request, event: dict) -> None:
    """WhatsApp to the support number, without personal data, at most once per error type every 30 min."""
    number = getattr(settings, "SUPPORT_WHATSAPP", "")
    if not number or settings.DEBUG:
        return
    signature = hashlib.sha1(f"{event['exception']}|{event['origin']}".encode()).hexdigest()
    if not cache.add(f"error-alert:{signature}", 1, ALERT_INTERVAL):
        return
    text = (
        f"Erro no sistema Don Corleone\n"
        f"Código: {event['code']}\n"
        f"Onde: {event['method']} {event['path'].split('?')[0]}\n"
        f"Erro: {event['exception'].rsplit('.', 1)[-1]}: {event['message'][:200]}\n"
        f"Detalhes: python manage.py ocorrencia {event['code']}"
    )
    tenant = getattr(request, "tenant", None)

    def send():
        from apps.integrations import evolution
        try:
            if evolution.is_configured():
                evolution.send_whatsapp_message(number, text, evolution.instance_name_for(tenant))
        except Exception:
            logger.exception("[Ocorrência %s] aviso no WhatsApp falhou", event["code"])

    threading.Thread(target=send, daemon=True).start()  # the error page does not wait for WhatsApp
