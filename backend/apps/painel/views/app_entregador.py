"""
Courier app (installable PWA): opened from a personal link sent by the manager.
Shows the orders in the bag with routes, today's earnings and the shift button.
Location itself is sent by Traccar Client to receber_localizacao.
"""
import json
import logging
from datetime import datetime, time, timedelta
from functools import wraps
from django.contrib import messages
from django.db.models import Sum
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from apps.delivery.models import CourierLocation, Employee
from apps.delivery.tracking import (
    SHOW_LAST_POSITION_FOR, end_shift, record_position, traccar_links, tracking_allowed, within_store_hours,
)
from apps.orders.models import Order
from apps.orders.services import OrderTransitionError, change_order_status
from .entregadores import delivered_orders

logger = logging.getLogger(__name__)
S = Order.Status
SESSION_ID, SESSION_TOKEN = "entregador_id", "entregador_token"
SESSION_DAYS = 90


def courier_app_view(view):
    """Pages of the courier app: requires the session opened by the personal link (revoked when the link is renewed)."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        token = request.session.get(SESSION_TOKEN)
        courier = None
        if token:
            courier = Employee.objects.filter(
                pk=request.session.get(SESSION_ID), access_token=token,
                role=Employee.Role.COURIER, is_active=True,
            ).select_related("tenant").first()
        if not courier:
            return render(request, "entregador/sem_acesso.html", status=403)
        request.courier = courier
        return view(request, *args, **kwargs)
    return wrapper


@never_cache
def entrar(request, token):
    courier = Employee.objects.filter(access_token=token, role=Employee.Role.COURIER, is_active=True).first()
    if not courier:
        return render(request, "entregador/sem_acesso.html", status=403)
    request.session.cycle_key()
    request.session[SESSION_ID] = str(courier.pk)
    request.session[SESSION_TOKEN] = token
    request.session.set_expiry(timedelta(days=SESSION_DAYS))
    return redirect("entregador:app")


@never_cache
@courier_app_view
def app(request):
    courier = request.courier
    today = timezone.localdate()
    start = timezone.make_aware(datetime.combine(today, time.min))
    end = timezone.make_aware(datetime.combine(today + timedelta(days=1), time.min))
    delivered = list(delivered_orders(courier.tenant, start, end).filter(courier=courier).order_by("-created_at"))
    location = CourierLocation.objects.filter(courier=courier).first()

    context = {
        "entregador": courier,
        "em_servico": courier.is_working_today,
        "loja_no_horario": within_store_hours(courier.tenant),
        "rastreando": tracking_allowed(courier),
        "localizacao": location,
        # Traccar is quiet while the phone is still: only warn when nothing ever arrived today
        "sem_sinal": courier.is_working_today and (not location or timezone.now() - location.recorded_at > SHOW_LAST_POSITION_FOR),
        "bag": courier.orders.filter(status=S.SAIU_PARA_ENTREGA).prefetch_related("items").order_by("created_at"),
        "entregues_hoje": delivered,
        "taxas_hoje": sum(o.delivery_fee for o in delivered),
        "vales_mes": courier.advances.filter(date__gte=today.replace(day=1)).aggregate(total=Sum("amount"))["total"] or 0,
        **traccar_links(request.build_absolute_uri(reverse("entregador:localizacao")), courier.access_token),
    }
    return render(request, "entregador/app.html", context)


@courier_app_view
def servico(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    courier = request.courier
    if courier.is_working_today:
        if courier.orders.filter(status=S.SAIU_PARA_ENTREGA).exists():
            messages.error(request, "Você ainda tem entregas na bag. Marque como entregue antes de encerrar.")
            return redirect("entregador:app")
        courier.working_on = None
        end_shift(courier)
        messages.success(request, "Serviço encerrado. Sua localização não é mais registrada.")
    else:
        courier.working_on = timezone.localdate()
        messages.success(request, "Bom trabalho! Você está em serviço.")
    courier.save(update_fields=["working_on", "updated_at"])
    return redirect("entregador:app")


@courier_app_view
def entregue(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    order = get_object_or_404(Order, pk=pk, courier=request.courier, tenant=request.courier.tenant)
    try:
        change_order_status(order, S.CONCLUIDO, notes=f"Entregue (confirmado por {request.courier.name} no app)")
    except OrderTransitionError as exc:
        messages.error(request, f"#{order.readable_code}: {exc}")
    else:
        messages.success(request, f"#{order.readable_code} entregue.")
    return redirect("entregador:app")


@courier_app_view
def manifest(request):
    """Per-courier manifest: the installed app opens through the personal link (iOS keeps its own cookies)."""
    data = {
        "name": "Don Corleone · Entregador",
        "short_name": "Entregas DC",
        "start_url": reverse("entregador:entrar", args=[request.courier.access_token]),
        "scope": reverse("entregador:app"),
        "display": "standalone",
        "background_color": "#0E0B09",
        "theme_color": "#0E0B09",
        "icons": [{"src": static("painel/brasao.svg"), "sizes": "any", "type": "image/svg+xml", "purpose": "any"}],
    }
    return HttpResponse(json.dumps(data), content_type="application/manifest+json")


def service_worker(request):
    """Only makes the app installable: nothing is cached, every page comes from the network."""
    script = "self.addEventListener('install', () => self.skipWaiting());\n" \
             "self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));\n"
    response = HttpResponse(script, content_type="application/javascript")
    response["Service-Worker-Allowed"] = reverse("entregador:app")
    response["Cache-Control"] = "no-cache"
    return response


@csrf_exempt  # called by Traccar Client, authenticated by the courier's personal code
def receber_localizacao(request):
    if request.method not in ("GET", "POST"):
        return HttpResponseNotAllowed(["GET", "POST"])
    outcome = record_position(request.POST if request.method == "POST" else request.GET)
    if outcome != "ok":
        logger.info("[Localização] ignorada: %s", outcome)
    # Always 200: Traccar would retry a rejected position forever, blocking the newer ones
    return HttpResponse("OK", content_type="text/plain")
