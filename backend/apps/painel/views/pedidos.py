from datetime import datetime, time, timedelta
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from apps.orders.models import Order, OrderStatusHistory
from apps.orders.services import (
    ACTION_LABELS, OPEN_STATUSES, OrderTransitionError, allowed_next_statuses, change_order_status,
)
from ..access import painel_view
from .common import nav_context
from .entregadores import courier_context

S = Order.Status
BOARD_COLUMNS = [
    ("novos", "Pendentes", [S.NOVO]),
    ("preparo", "Em preparo", [S.CONFIRMADO, S.PREPARO]),
    ("rota", "Enviados / no balcão", [S.SAIU_PARA_ENTREGA, S.PRONTO_RETIRADA]),
]


def _with_actions(order):
    order.acoes = [
        {"status": status, "rotulo": ACTION_LABELS[status], "cancelar": status == S.CANCELADO}
        for status in allowed_next_statuses(order)
    ]
    return order


def _board_context(tenant):
    open_orders = (
        Order.objects.filter(tenant=tenant, status__in=OPEN_STATUSES)
        .select_related("courier").prefetch_related("items__flavors").order_by("created_at")
    )
    columns = []
    for key, title, statuses in BOARD_COLUMNS:
        cards = [_with_actions(o) for o in open_orders if o.status in statuses]
        columns.append({"chave": key, "titulo": title, "pedidos": cards})

    today_start = timezone.make_aware(datetime.combine(timezone.localdate(), time.min))
    closed_today = OrderStatusHistory.objects.filter(order__tenant=tenant, created_at__gte=today_start)
    return {
        **courier_context(tenant),
        "colunas": columns,
        "qtd_novos": len(columns[0]["pedidos"]),
        "concluidos_hoje": closed_today.filter(status=S.CONCLUIDO).count(),
        "cancelados_hoje": closed_today.filter(status=S.CANCELADO).count(),
        "atualizado_em": timezone.localtime(),
    }


@painel_view
def quadro(request):
    context = {**nav_context(request, "pedidos"), **_board_context(request.tenant)}
    return render(request, "painel/pedidos/quadro.html", context)


@painel_view
def quadro_parcial(request):
    """Board columns only: refreshed by painel.js every few seconds."""
    return render(request, "painel/pedidos/_quadro.html", _board_context(request.tenant))


@painel_view
def lista(request):
    orders = Order.objects.filter(tenant=request.tenant)

    busca = request.GET.get("busca", "").strip()
    if busca:
        digits = "".join(filter(str.isdigit, busca))
        query = Q(readable_code__icontains=busca) | Q(customer_name__icontains=busca)
        if len(digits) >= 4:
            query |= Q(customer_phone__contains=digits)
        orders = orders.filter(query)

    status = request.GET.get("status", "")
    if status in S.values:
        orders = orders.filter(status=status)
    modalidade = request.GET.get("modalidade", "")
    if modalidade in Order.FulfillmentMode.values:
        orders = orders.filter(fulfillment_mode=modalidade)

    de, ate = request.GET.get("de", ""), request.GET.get("ate", "")
    try:
        if de:
            orders = orders.filter(created_at__gte=timezone.make_aware(datetime.combine(datetime.strptime(de, "%Y-%m-%d").date(), time.min)))
        if ate:
            end = datetime.strptime(ate, "%Y-%m-%d").date() + timedelta(days=1)
            orders = orders.filter(created_at__lt=timezone.make_aware(datetime.combine(end, time.min)))
    except ValueError:
        messages.error(request, "Data inválida no filtro.")

    totals = orders.exclude(status=S.CANCELADO).aggregate(total=Sum("total_amount"))
    page = Paginator(orders.order_by("-created_at"), 30).get_page(request.GET.get("pagina"))
    context = {
        **nav_context(request, "pedidos"),
        "pagina": page,
        "total_filtrado": totals["total"],
        "qtd_filtrado": page.paginator.count,
        "status_opcoes": S.choices,
        "modalidade_opcoes": Order.FulfillmentMode.choices,
        "filtros": {"busca": busca, "status": status, "modalidade": modalidade, "de": de, "ate": ate},
    }
    return render(request, "painel/pedidos/lista.html", context)


@painel_view
def detalhe(request, pk):
    order = get_object_or_404(
        Order.objects.select_related("courier").prefetch_related("items__flavors", "status_history__changed_by"),
        pk=pk, tenant=request.tenant,
    )
    context = {**nav_context(request, "pedidos"), **courier_context(request.tenant), "pedido": _with_actions(order)}
    return render(request, "painel/pedidos/detalhe.html", context)


@painel_view
def mudar_status(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    order = get_object_or_404(Order, pk=pk, tenant=request.tenant)
    new_status = request.POST.get("status", "")
    try:
        whatsapp = change_order_status(
            order, new_status, user=request.user, notes=request.POST.get("motivo", ""),
            courier_id=request.POST.get("entregador"),
        )
    except OrderTransitionError as exc:
        messages.error(request, f"#{order.readable_code}: {exc}")
    else:
        text = f"#{order.readable_code}: {order.get_status_display()}"
        text += f" com {order.courier.name}." if new_status == S.SAIU_PARA_ENTREGA and order.courier else "."
        if new_status in (S.SAIU_PARA_ENTREGA, S.PRONTO_RETIRADA):
            text += " Cliente avisado no WhatsApp." if whatsapp else " Aviso automático no WhatsApp não enviado (Evolution API não configurada)."
        messages.success(request, text)

    next_url = request.POST.get("next", "")
    if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect("painel:pedido", pk=order.pk)
