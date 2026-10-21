from datetime import timedelta
from decimal import Decimal
from django.db.models import Count, Sum
from django.shortcuts import render
from django.utils import timezone
from apps.catalog.models import Product
from apps.orders.models import Order, OrderItem, OrderItemFlavor
from apps.orders.services import OPEN_STATUSES
from apps.orders.serializers import PRICE_ON_REQUEST_NOTE
from ..access import painel_view
from .common import PERIODS, nav_context, period_range

WAITING_ALERT_MINUTES = 5


@painel_view
def dashboard(request):
    tenant = request.tenant
    start, end, period, period_label = period_range(request.GET.get("periodo", "hoje"))

    orders = Order.objects.filter(tenant=tenant, created_at__gte=start, created_at__lt=end)
    valid = orders.exclude(status=Order.Status.CANCELADO)
    registered = valid.aggregate(total=Sum("total_amount"), count=Count("id"))
    completed = valid.filter(status=Order.Status.CONCLUIDO).aggregate(total=Sum("total_amount"), count=Count("id"))
    registered_total = registered["total"] or Decimal("0.00")
    registered_count = registered["count"] or 0

    open_orders = Order.objects.filter(tenant=tenant, status__in=OPEN_STATUSES)
    open_by_status = dict(open_orders.values_list("status").annotate(n=Count("id")))

    waiting_since = timezone.now() - timedelta(minutes=WAITING_ALERT_MINUTES)
    alerts = []
    late = open_orders.filter(status=Order.Status.NOVO, created_at__lt=waiting_since).count()
    if late:
        alerts.append({
            "tom": "perigo",
            "texto": f"{late} pedido(s) aguardando confirmação há mais de {WAITING_ALERT_MINUTES} min.",
            "link": "painel:pedidos",
        })
    pending_fee = open_orders.filter(notes__contains="TAXA DE ENTREGA A CONFIRMAR").count()
    if pending_fee:
        alerts.append({
            "tom": "aviso",
            "texto": f"{pending_fee} pedido(s) em aberto com taxa de entrega a confirmar (bairro fora da lista).",
            "link": "painel:pedidos",
        })
    price_on_request = OrderItem.objects.filter(order__in=open_orders, notes__contains=PRICE_ON_REQUEST_NOTE).values("order").distinct().count()
    if price_on_request:
        alerts.append({
            "tom": "aviso",
            "texto": f"{price_on_request} pedido(s) em aberto com item \"sob consulta\": combine o preço com o cliente.",
            "link": "painel:pedidos",
        })
    sold_out = Product.objects.filter(tenant=tenant, is_available=False, category__is_active=True).count()
    if sold_out:
        alerts.append({
            "tom": "info",
            "texto": f"{sold_out} produto(s) marcados como esgotados no cardápio.",
            "link": "painel:cardapio",
        })

    top_items = (
        OrderItem.objects.filter(order__in=valid, product_type_snapshot__in=["simple", "kit_esfiha", "combo"])
        .values("product_name_snapshot").annotate(qtd=Sum("quantity")).order_by("-qtd")[:5]
    )
    top_flavors = (
        OrderItemFlavor.objects.filter(item__order__in=valid)
        .values("flavor_name_snapshot").annotate(qtd=Count("id")).order_by("-qtd")[:5]
    )

    context = {
        **nav_context(request, "dashboard"),
        "periodo": period,
        "periodo_label": period_label,
        "periodos": [(key, label) for key, (label, _) in PERIODS.items()],
        "valor_registrado": registered_total,
        "qtd_pedidos": registered_count,
        "ticket_medio": (registered_total / registered_count) if registered_count else None,
        "valor_concluido": completed["total"] or Decimal("0.00"),
        "qtd_concluidos": completed["count"] or 0,
        "qtd_cancelados": orders.filter(status=Order.Status.CANCELADO).count(),
        "em_aberto": open_orders.count(),
        "em_aberto_por_status": [
            ("Pendentes", open_by_status.get(Order.Status.NOVO, 0), "novo"),
            ("Em preparo",
             open_by_status.get(Order.Status.CONFIRMADO, 0) + open_by_status.get(Order.Status.PREPARO, 0),
             "preparo"),
            ("Enviados / no balcão",
             open_by_status.get(Order.Status.SAIU_PARA_ENTREGA, 0) + open_by_status.get(Order.Status.PRONTO_RETIRADA, 0),
             "rota"),
        ],
        "alertas": alerts,
        "top_sabores": top_flavors,
        "top_itens": top_items,
        "ultimos_pedidos": orders.order_by("-created_at")[:8],
    }
    return render(request, "painel/dashboard.html", context)
