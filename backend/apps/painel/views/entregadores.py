"""Delivery riders: who is working today, dispatching orders and how much each one receives."""
from datetime import datetime, time, timedelta
from django.contrib import messages
from django.db.models import Count, Prefetch, Q, Sum
from django.db.models.deletion import ProtectedError
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from apps.delivery.models import CourierLocation, Employee, SalaryAdvance
from apps.delivery.tracking import (
    SHOW_LAST_POSITION_FOR, STOPPED_AFTER, end_shift, traccar_links, within_store_hours,
)
from apps.integrations import evolution
from apps.orders.models import Order, OrderStatusHistory
from apps.orders.services import OrderTransitionError, change_order_status
from ..access import painel_view
from ..forms import CourierForm
from .common import PERIODS, nav_context, period_range

S = Order.Status


def couriers(tenant):
    return Employee.objects.filter(tenant=tenant, role=Employee.Role.COURIER)


def courier_context(tenant) -> dict:
    """What the "Saiu para entrega" buttons need to offer a courier."""
    active = couriers(tenant).filter(is_active=True)
    return {
        "entregadores_hoje": list(active.filter(working_on=timezone.localdate())),
        "usa_entregadores": active.exists(),
    }


def _period(request):
    """(start, end, period key, label, day) from ?periodo= or a specific ?dia=YYYY-MM-DD."""
    day = request.GET.get("dia", "")
    if day:
        try:
            date = datetime.strptime(day, "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "Data inválida no filtro.")
        else:
            start = timezone.make_aware(datetime.combine(date, time.min))
            end = timezone.make_aware(datetime.combine(date + timedelta(days=1), time.min))
            return start, end, "", date.strftime("%d/%m/%Y"), day
    start, end, key, label = period_range(request.GET.get("periodo", ""))
    return start, end, key, label, ""


def delivered_orders(tenant, start, end):
    """Orders a courier delivered (marked as completed) within the period."""
    return Order.objects.filter(
        tenant=tenant, courier__isnull=False, status=S.CONCLUIDO,
        status_history__status=S.CONCLUIDO,
        status_history__created_at__gte=start, status_history__created_at__lt=end,
    )


def app_access_context(request, courier) -> dict:
    """Links shown in the "App do entregador" section (courier and staff pages)."""
    server_url = request.build_absolute_uri(reverse("entregador:localizacao"))
    return {
        **traccar_links(server_url, courier.access_token or ""),
        "link_app": request.build_absolute_uri(reverse("entregador:entrar", args=[courier.access_token]))
        if courier.access_token else "",
        "endereco_local": request.get_host().split(":")[0] in ("localhost", "127.0.0.1"),
    }


def _sheet(tenant, start, end, rows):
    """
    The riders' spreadsheet: one column per courier with every order they took out in the
    period (or still have in the bag), what is already paid ("pg") and what they must collect.
    """
    orders = (
        Order.objects.filter(tenant=tenant, courier__isnull=False).exclude(status=S.CANCELADO)
        .filter(Q(status=S.SAIU_PARA_ENTREGA) | Q(
            status_history__status=S.SAIU_PARA_ENTREGA,
            status_history__created_at__gte=start, status_history__created_at__lt=end,
        ))
        .distinct().order_by("created_at")
    )
    by_courier = {}
    for order in orders:
        order.pago = order.payment_method == Order.PaymentMethod.PIX
        by_courier.setdefault(order.courier_id, []).append(order)

    columns = []
    for row in rows:
        courier_orders = by_courier.get(row["entregador"].pk, [])
        if not courier_orders and not row["trabalhando"]:
            continue
        columns.append({
            **row,
            "pedidos": courier_orders,
            "a_cobrar": sum(o.total_amount for o in courier_orders if not o.pago),
        })
    return columns


def _period_context(request):
    start, end, key, label, day = _period(request)
    return start, end, {
        "periodos": [(k, v[0]) for k, v in PERIODS.items()],
        "periodo": key,
        "periodo_label": label,
        "dia": day,
    }


def _redirect_back(request, fallback="painel:entregadores"):
    next_url = request.POST.get("next", "")
    if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect(fallback)


@painel_view
def entregadores(request):
    tenant = request.tenant
    if request.method == "POST":
        form = CourierForm(request.POST, tenant=tenant)
        if form.is_valid():
            courier = form.save(commit=False)
            courier.working_on = timezone.localdate()
            courier.save()
            messages.success(request, f"{courier.name} cadastrado e marcado como trabalhando hoje.")
            return redirect("painel:entregadores")
    else:
        form = CourierForm(tenant=tenant)

    start, end, period = _period_context(request)
    totals = {
        row["courier"]: row
        for row in delivered_orders(tenant, start, end).values("courier").annotate(qtd=Count("id"), taxas=Sum("delivery_fee"))
    }
    on_route = list(
        Order.objects.filter(tenant=tenant, status=S.SAIU_PARA_ENTREGA)
        .select_related("courier").order_by("updated_at")
    )
    advances = dict(
        SalaryAdvance.objects.filter(tenant=tenant, date__gte=start.date(), date__lt=end.date())
        .values_list("employee").annotate(total=Sum("amount"))
    )
    today = timezone.localdate()

    rows = []
    # Couriers who left the team still show up for the periods in which they delivered
    for courier in couriers(tenant).filter(Q(is_active=True) | Q(pk__in=totals.keys())):
        total = totals.get(courier.pk, {})
        rows.append({
            "entregador": courier,
            "trabalhando": courier.is_active and courier.working_on == today,
            "em_rota": sum(1 for o in on_route if o.courier_id == courier.pk),
            "qtd": total.get("qtd", 0),
            "taxas": total.get("taxas") or 0,
            "vales": advances.get(courier.pk) or 0,
        })
    # Working today first, then whoever delivered in the period
    rows.sort(key=lambda r: (not r["trabalhando"], not r["qtd"], r["entregador"].name.lower()))

    route_groups = {}
    for order in on_route:
        route_groups.setdefault(order.courier, []).append(order)

    context = {
        **nav_context(request, "entregadores"),
        **period,
        **courier_context(tenant),
        "form": form,
        "linhas": rows,
        "planilha": _sheet(tenant, start, end, rows),
        "em_rota": [{"entregador": c, "pedidos": orders} for c, orders in route_groups.items()],
        "qtd_em_rota": len(on_route),
        "qtd_trabalhando": sum(1 for r in rows if r["trabalhando"]),
        "qtd_entregas": sum(r["qtd"] for r in rows),
        "total_taxas": sum(r["taxas"] for r in rows),
        "prontos": Order.objects.filter(
            tenant=tenant, fulfillment_mode=Order.FulfillmentMode.DELIVERY, status__in=[S.CONFIRMADO, S.PREPARO],
        ).order_by("created_at"),
    }
    return render(request, "painel/entregadores/lista.html", context)


@painel_view
def entregador(request, pk):
    tenant = request.tenant
    courier = get_object_or_404(couriers(tenant), pk=pk)
    if request.method == "POST":
        form = CourierForm(request.POST, instance=courier, tenant=tenant)
        if form.is_valid():
            form.save()
            messages.success(request, "Entregador salvo.")
            return redirect("painel:entregador", pk=courier.pk)
    else:
        form = CourierForm(instance=courier, tenant=tenant)

    start, end, period = _period_context(request)
    history = Prefetch("status_history", queryset=OrderStatusHistory.objects.filter(
        status__in=[S.SAIU_PARA_ENTREGA, S.CONCLUIDO],
    ))
    delivered = list(
        delivered_orders(tenant, start, end).filter(courier=courier)
        .prefetch_related(history).order_by("-created_at")
    )
    for order in delivered:
        times = {h.status: h.created_at for h in order.status_history.all()}
        order.saiu_em = times.get(S.SAIU_PARA_ENTREGA)
        order.entregue_em = times.get(S.CONCLUIDO)

    context = {
        **nav_context(request, "entregadores"),
        **period,
        "entregador": courier,
        "form": form,
        "entregues": delivered,
        "total_taxas": sum(o.delivery_fee for o in delivered),
        "em_rota": courier.orders.filter(status=S.SAIU_PARA_ENTREGA).order_by("updated_at"),
        "vales": courier.advances.filter(date__gte=start.date(), date__lt=end.date()),
        **app_access_context(request, courier),
    }
    return render(request, "painel/entregadores/detalhe.html", context)


@painel_view
def entregador_trabalhando(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    courier = get_object_or_404(couriers(request.tenant), pk=pk)
    courier.working_on = None if courier.is_working_today else timezone.localdate()
    courier.save(update_fields=["working_on", "updated_at"])
    if courier.working_on:
        messages.success(request, f"{courier.name} está trabalhando hoje.")
    else:
        end_shift(courier)
        messages.success(request, f"{courier.name} marcado como fora hoje.")
    return _redirect_back(request)


@painel_view
def entregador_acesso(request, pk):
    """Creates/renews the courier's app link and optionally sends it on WhatsApp."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    courier = get_object_or_404(couriers(request.tenant).filter(is_active=True), pk=pk)
    if request.POST.get("acao") == "enviar" and courier.access_token:
        link = request.build_absolute_uri(reverse("entregador:entrar", args=[courier.access_token]))
        text = (f"Olá, {courier.name}! Este é o seu acesso ao app de entregas da {request.tenant.name}:\n{link}\n\n"
                "Abra no celular, toque em \"Adicionar à tela inicial\" e siga o passo a passo para ligar o Traccar Client.")
        if courier.phone and evolution.is_configured() and evolution.send_whatsapp_message(
            courier.phone, text, evolution.instance_name_for(request.tenant),
        ):
            messages.success(request, f"Link enviado para o WhatsApp de {courier.name}.")
        else:
            messages.error(request, "Não foi possível enviar pelo WhatsApp (confira o número e a conexão em WhatsApp). Copie o link e envie manualmente.")
    else:
        renewing = bool(courier.access_token)
        courier.new_access_token()
        end_shift(courier)
        messages.success(request, "Novo link gerado. O link antigo parou de funcionar: envie o novo e atualize o Traccar."
                         if renewing else "Link de acesso gerado.")
    next_url = request.POST.get("next", "")
    if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(f"{next_url}#app-entregador")
    return redirect(f"{reverse('painel:entregador', args=[courier.pk])}#app-entregador")


@painel_view
def mapa(request):
    return render(request, "painel/entregadores/mapa.html", {**nav_context(request, "entregadores")})


@painel_view
def mapa_posicoes(request):
    """Polled by the map every 10 s: couriers on duty today and their last position."""
    on_duty = (
        couriers(request.tenant).filter(is_active=True, working_on=timezone.localdate())
        .select_related("location").annotate(na_rua=Count("orders", filter=Q(orders__status=S.SAIU_PARA_ENTREGA)))
    )
    now = timezone.now()
    data = []
    for courier in on_duty:
        try:
            location = courier.location
        except CourierLocation.DoesNotExist:
            location = None
        fresh = bool(location) and now - location.recorded_at <= SHOW_LAST_POSITION_FOR
        data.append({
            "parado": fresh and now - location.recorded_at > STOPPED_AFTER,
            "id": str(courier.pk),
            "nome": courier.name,
            "iniciais": "".join(part[0] for part in courier.name.split()[:2]).upper(),
            "na_rua": courier.na_rua,
            "lat": float(location.latitude) if fresh else None,
            "lon": float(location.longitude) if fresh else None,
            "ha_segundos": int((now - location.recorded_at).total_seconds()) if fresh else None,
            "bateria": location.battery if fresh else None,
            "precisao": round(location.accuracy) if fresh and location.accuracy else None,
            "tem_app": bool(courier.access_token),
            "detalhe": reverse("painel:entregador", args=[courier.pk]),
        })
    return JsonResponse({"entregadores": data, "loja_no_horario": within_store_hours(request.tenant)})


@painel_view
def entregador_excluir(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    courier = get_object_or_404(couriers(request.tenant), pk=pk)
    try:
        courier.delete()
    except ProtectedError:
        messages.error(request, f"{courier.name} tem entregas ou vales e fica no histórico. "
                                "Para tirar da lista, desmarque \"Na equipe\" em Funcionários.")
        return redirect("painel:entregador", pk=courier.pk)
    messages.success(request, f"{courier.name} removido.")
    return redirect("painel:entregadores")


@painel_view
def despachar(request):
    """Several orders leaving together in the same rider's bag."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    tenant = request.tenant
    orders = list(Order.objects.filter(tenant=tenant, pk__in=request.POST.getlist("pedidos")).order_by("created_at"))
    if not orders:
        messages.error(request, "Marque os pedidos que vão sair na bag.")
        return _redirect_back(request)

    courier_id = request.POST.get("entregador", "")
    sent, notified, errors = [], 0, []
    for order in orders:
        try:
            notified += change_order_status(order, S.SAIU_PARA_ENTREGA, user=request.user, courier_id=courier_id)
        except OrderTransitionError as exc:
            errors.append(f"#{order.readable_code}: {exc}")
        else:
            sent.append(order)

    if sent:
        name = sent[0].courier.name if sent[0].courier else "o entregador"
        codes = ", ".join(f"#{o.readable_code}" for o in sent)
        messages.success(request, f"{len(sent)} pedido{'s' if len(sent) > 1 else ''} saiu com {name}: {codes}. "
                                  f"Clientes avisados no WhatsApp: {notified}.")
    for error in errors:
        messages.error(request, error)
    return _redirect_back(request)
