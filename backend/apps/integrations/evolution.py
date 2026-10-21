"""
Evolution API (v2) integration for Don Corleone.
Manages each store's WhatsApp instance (create, QR code, status, logout) and sends the
automatic messages: order dispatched for delivery and order ready for pickup.
"""
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 8


class EvolutionError(Exception):
    """Evolution API unreachable, not configured or refusing the request (message is user-facing)."""


def format_whatsapp_number(number: str) -> str:
    """Sanitizes phone number to format 55659XXXXXXXX."""
    digits = ''.join(filter(str.isdigit, number or ''))
    if digits.startswith('55'):
        return digits
    if len(digits) in [10, 11]:
        return f"55{digits}"
    return digits


def is_configured() -> bool:
    return bool(settings.EVOLUTION_API_URL and settings.EVOLUTION_API_KEY)


def instance_name_for(tenant) -> str:
    """Instance chosen in the panel, or the default from the environment."""
    from apps.delivery.models import StoreSettings
    store = StoreSettings.objects.filter(tenant=tenant).first()
    return (store.whatsapp_instance if store else "") or settings.EVOLUTION_INSTANCE


def _request(method: str, path: str, **kwargs):
    """Calls the Evolution API with the master key. Returns (status_code, json body)."""
    if not is_configured():
        raise EvolutionError("Evolution API não configurada (EVOLUTION_API_URL / EVOLUTION_API_KEY).")
    try:
        response = requests.request(
            method,
            f"{settings.EVOLUTION_API_URL}{path}",
            headers={"apikey": settings.EVOLUTION_API_KEY},
            timeout=TIMEOUT_SECONDS,
            **kwargs,
        )
    except requests.RequestException as exc:
        logger.warning("[Evolution API] Falha de conexão em %s: %s", path, exc)
        raise EvolutionError("Não foi possível conectar à Evolution API. Confira se o container está rodando.") from exc

    try:
        body = response.json()
    except ValueError:
        body = {}
    if response.status_code == 401:
        raise EvolutionError("A Evolution API recusou a chave. Confira EVOLUTION_API_KEY no .env.")
    return response.status_code, body


def _error_message(body) -> str:
    """
    Running v2 servers answer {"response": {"message": ["..."]}}; the published docs show
    {"error": {"code": "...", "message": "..."}}. Both are accepted.
    """
    if not isinstance(body, dict):
        return "resposta inesperada"
    error = body.get("error")
    if isinstance(error, dict) and error.get("message"):
        return str(error["message"])
    messages = (body.get("response") or {}).get("message")
    if isinstance(messages, list) and messages:
        return str(messages[0])
    return str(messages or "resposta inesperada")


def _qr_from(body) -> str | None:
    """data:image/png;base64,... from a create/connect response, when there is one."""
    if not isinstance(body, dict):
        return None
    qr = body.get("qrcode") if isinstance(body.get("qrcode"), dict) else body
    return qr.get("base64") or None


def connection_state(instance: str) -> str:
    """'open' (connected), 'connecting', 'close' or 'missing' (instance does not exist)."""
    status, body = _request("GET", f"/instance/connectionState/{instance}")
    if status == 404:
        return "missing"
    if status >= 400:
        raise EvolutionError(f"Erro ao consultar a instância: {_error_message(body)}")
    return (body.get("instance") or {}).get("state") or "close"


def instance_profile(instance: str) -> dict:
    """Connected number and profile name (empty when not available)."""
    status, body = _request("GET", "/instance/fetchInstances", params={"instanceName": instance})
    if status >= 400 or not isinstance(body, list):
        return {}
    # Items come flat ({"name", "ownerJid", ...}) on running servers and wrapped in
    # {"instance": {...}} in the docs; the filter param is undocumented, so match the name here too.
    for item in body:
        data = item.get("instance", item) if isinstance(item, dict) else {}
        if (data.get("name") or data.get("instanceName")) in (instance, None):
            owner = (data.get("ownerJid") or data.get("owner") or "").split("@")[0]
            return {"numero": owner, "nome": data.get("profileName") or ""}
    return {}


def connect_instance(instance: str) -> dict:
    """
    Creates the instance when it does not exist yet, then asks for a QR code.
    Returns {"state": ..., "qr": "data:image/png;base64,..." or None}.
    """
    state = connection_state(instance)
    if state == "open":
        return {"state": "open", "qr": None}

    if state == "missing":
        status, body = _request("POST", "/instance/create", json={
            "instanceName": instance,
            "integration": "WHATSAPP-BAILEYS",
            "qrcode": True,
        })
        if status >= 400:
            raise EvolutionError(f"Erro ao criar a instância: {_error_message(body)}")
        qr = _qr_from(body)
        if qr:
            return {"state": "connecting", "qr": qr}

    status, body = _request("GET", f"/instance/connect/{instance}")
    if status >= 400:
        raise EvolutionError(f"Erro ao gerar o QR Code: {_error_message(body)}")
    if (body.get("instance") or {}).get("state") == "open":
        return {"state": "open", "qr": None}
    return {"state": "connecting", "qr": _qr_from(body)}


def logout_instance(instance: str) -> None:
    status, body = _request("DELETE", f"/instance/logout/{instance}")
    if status >= 400 and status != 404:
        raise EvolutionError(f"Erro ao desconectar: {_error_message(body)}")


def send_whatsapp_message(phone_number: str, text: str, instance: str | None = None) -> bool:
    """Sends a text message. Never raises: order status changes must not fail because of WhatsApp."""
    instance = instance or settings.EVOLUTION_INSTANCE
    if not is_configured():
        logger.info("[Evolution API] Não configurada. Mensagem simulada para %s:\n%s", phone_number, text)
        return False

    sanitized_phone = format_whatsapp_number(phone_number)
    path = f"/message/sendText/{instance}"
    try:
        status, body = _request("POST", path, json={"number": sanitized_phone, "text": text, "delay": 1200})
        if status == 400:
            # The published docs describe the body as {"textMessage": {"text"}}: retry in that shape
            status, body = _request("POST", path, json={
                "number": sanitized_phone, "textMessage": {"text": text}, "delay": 1200,
            })
    except EvolutionError as exc:
        logger.error("[Evolution API] %s", exc)
        return False

    if status in (200, 201):
        logger.info("[Evolution API] Mensagem enviada para %s", sanitized_phone)
        return True
    logger.warning("[Evolution API] Erro ao enviar mensagem (%s): %s", status, body)
    return False


def send_order_dispatched_notification(order) -> bool:
    """Dispatches automatic notification when order status becomes 'SAIU_PARA_ENTREGA'."""
    phone = order.customer_phone
    if not phone:
        return False

    first_name = (order.customer_name or 'Cliente').split()[0]
    # The site opens the tracking screen from the ?rastreio= parameter
    tracking_url = f"{settings.SITE_PUBLIC_URL}/?rastreio={order.readable_code}"

    message = (
        f"🍕 *DON CORLEONE — PEDIDO A CAMINHO!* 🛵💨\n\n"
        f"Olá, *{first_name}*!\n"
        f"Seu pedido *#{order.readable_code}* acabou de sair para entrega com o nosso entregador!\n\n"
        f"📍 *Acompanhe seu pedido:*\n"
        f"{tracking_url}\n\n"
        f"Obrigado pela preferência e bom apetite! 💛"
    )

    return send_whatsapp_message(phone, message, instance_name_for(order.tenant))


def send_order_ready_pickup_notification(order) -> bool:
    """Dispatches automatic notification when order status becomes 'PRONTO_RETIRADA'."""
    phone = order.customer_phone
    if not phone:
        return False

    first_name = (order.customer_name or 'Cliente').split()[0]
    address = "Avenida Brasil, 2055, Cidade Alta"

    message = (
        f"🍕 *DON CORLEONE — PEDIDO PRONTO!* 🏪\n\n"
        f"Olá, *{first_name}*!\n"
        f"Seu pedido *#{order.readable_code}* está quentinho e pronto para retirada no balcão!\n\n"
        f"📍 *Endereço da nossa unidade:*\n"
        f"{address}\n\n"
        f"Estamos te esperando! 💛"
    )

    return send_whatsapp_message(phone, message, instance_name_for(order.tenant))
