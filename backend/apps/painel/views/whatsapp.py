"""WhatsApp connection page: creates the store's Evolution API instance and shows the QR code."""
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import validate_slug
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import redirect, render
from apps.delivery.models import StoreSettings
from apps.integrations import evolution
from ..access import painel_view
from .common import nav_context

STATE_LABELS = {
    "open": "Conectado",
    "connecting": "Aguardando leitura do QR Code",
    "close": "Desconectado",
    "missing": "Instância ainda não criada",
}


def _store(tenant):
    store, _ = StoreSettings.objects.get_or_create(tenant=tenant)
    return store


def _page(request, qr=None, erro=""):
    instance = evolution.instance_name_for(request.tenant)
    state, profile = "close", {}
    if evolution.is_configured() and not erro:
        try:
            state = evolution.connection_state(instance)
            if state == "open":
                profile = evolution.instance_profile(instance)
        except evolution.EvolutionError as exc:
            erro = str(exc)
    if qr and state != "open":
        state = "connecting"

    return render(request, "painel/whatsapp.html", {
        **nav_context(request, "whatsapp"),
        "configurado": evolution.is_configured(),
        "api_url": settings.EVOLUTION_API_URL,
        "instancia": instance,
        "estado": state,
        "estado_texto": STATE_LABELS.get(state, state),
        "perfil": profile,
        "qr": qr,
        "erro": erro,
    })


@painel_view
def whatsapp(request):
    return _page(request)


@painel_view
def whatsapp_conectar(request):
    """Saves the instance name, creates the instance if needed and shows the QR code."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    name = request.POST.get("instancia", "").strip().lower()
    try:
        validate_slug(name)
    except ValidationError:
        messages.error(request, "Use só letras minúsculas, números e hífen no nome da instância (ex.: don-corleone).")
        return redirect("painel:whatsapp")

    store = _store(request.tenant)
    if store.whatsapp_instance != name:
        store.whatsapp_instance = name
        store.save(update_fields=["whatsapp_instance", "updated_at"])

    try:
        result = evolution.connect_instance(name)
    except evolution.EvolutionError as exc:
        return _page(request, erro=f"Erro ao preparar a instância: {exc}")
    if result["state"] == "open":
        messages.success(request, "O WhatsApp já está conectado.")
        return redirect("painel:whatsapp")
    return _page(request, qr=result["qr"])


@painel_view
def whatsapp_estado(request):
    """Polled by the page while the QR code is on screen. ?qr=1 also returns a fresh QR code."""
    instance = evolution.instance_name_for(request.tenant)
    try:
        if request.GET.get("qr") == "1":
            result = evolution.connect_instance(instance)
            return JsonResponse({"estado": result["state"], "qr": result["qr"]})
        return JsonResponse({"estado": evolution.connection_state(instance)})
    except evolution.EvolutionError as exc:
        return JsonResponse({"estado": "erro", "erro": str(exc)}, status=502)


@painel_view
def whatsapp_desconectar(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    try:
        evolution.logout_instance(evolution.instance_name_for(request.tenant))
    except evolution.EvolutionError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "WhatsApp desconectado. Os avisos automáticos ficam pausados até conectar de novo.")
    return redirect("painel:whatsapp")


@painel_view
def whatsapp_teste(request):
    """Sends a test message so the owner can check the connection end to end."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    phone = "".join(filter(str.isdigit, request.POST.get("telefone", "")))
    if len(phone) < 10:
        messages.error(request, "Informe um número com DDD para o teste.")
        return redirect("painel:whatsapp")

    sent = evolution.send_whatsapp_message(
        phone,
        "✅ Teste do painel Don Corleone: os avisos automáticos de pedido estão funcionando.",
        evolution.instance_name_for(request.tenant),
    )
    if sent:
        messages.success(request, "Mensagem de teste enviada.")
    else:
        messages.error(request, "Não foi possível enviar a mensagem de teste. Confira se o WhatsApp está conectado.")
    return redirect("painel:whatsapp")
