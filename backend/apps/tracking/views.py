from datetime import timedelta
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from apps.delivery.models import DeliveryZone, StoreSettings
from apps.orders.models import Order

S = Order.Status

# Customer-facing step of each status. CONFIRMADO is legacy and shows as "Em preparo".
STEP_BY_STATUS = {
    S.NOVO: 1,
    S.CONFIRMADO: 2,
    S.PREPARO: 2,
    S.SAIU_PARA_ENTREGA: 3,
    S.PRONTO_RETIRADA: 3,
    S.CONCLUIDO: 4,
}
STATUSES_BY_STEP = {
    1: [S.NOVO],
    2: [S.CONFIRMADO, S.PREPARO],
    3: [S.SAIU_PARA_ENTREGA, S.PRONTO_RETIRADA],
    4: [S.CONCLUIDO],
}


def _hhmm(dt):
    return timezone.localtime(dt).strftime('%H:%M') if dt else None


def _step_times(order) -> dict:
    """First time the order reached each step, from the status history."""
    times = {}
    for entry in order.status_history.all():
        for step, statuses in STATUSES_BY_STEP.items():
            if entry.status in statuses and step not in times:
                times[step] = entry.created_at
    times.setdefault(1, order.created_at)
    return times


def _forecast(order, step_times, current_step) -> str | None:
    """Delivery window like 'Chega entre 20:10 e 20:30', counted from the confirmation."""
    if current_step not in (2, 3) or 2 not in step_times:
        return None
    store = StoreSettings.objects.filter(tenant=order.tenant).first()
    if order.fulfillment_mode == Order.FulfillmentMode.PICKUP:
        if current_step == 3:
            return None
        return f"Pronto para retirada em {store.pickup_time_text}" if store else None

    zone = DeliveryZone.objects.filter(
        tenant=order.tenant, neighborhood__iexact=order.delivery_neighborhood, is_active=True
    ).first()
    if not zone:
        return f"Entrega em {store.delivery_time_text}" if store else None
    latest = step_times[2] + timedelta(minutes=zone.estimated_minutes)
    earliest = latest - timedelta(minutes=20)
    return f"Chega entre {_hhmm(earliest)} e {_hhmm(latest)}"


class OrderTrackingView(APIView):
    """
    Public tracking view for customers (Mercado Livre style progress timeline).
    Accessible via readable_code (e.g. DC-1310-74K) or order UUID.
    """
    permission_classes = [AllowAny]
    # Order codes are short: limit lookups so nobody can enumerate other customers' orders
    throttle_scope = 'tracking'

    def get(self, request, code):
        order = Order.objects.filter(readable_code__iexact=code.strip()).first()
        if not order:
            try:
                order = Order.objects.filter(id=code.strip()).first()
            except Exception:
                pass

        if not order:
            return Response(
                {"error": "Pedido não encontrado. Verifique o código informado."},
                status=status.HTTP_404_NOT_FOUND
            )

        is_delivery = order.fulfillment_mode == Order.FulfillmentMode.DELIVERY
        is_cancelled = order.status == S.CANCELADO
        step_times = _step_times(order)
        # A cancelled order keeps the timeline frozen at the last step it reached
        current_step = max(step_times) if is_cancelled else STEP_BY_STATUS.get(order.status, 1)

        steps = [
            ("Pendente", "Aguardando a pizzaria confirmar seu pedido", "📝"),
            ("Em preparo", "Pedido confirmado e sendo preparado", "👨‍🍳"),
            ("Enviado", "Saiu para entrega com o motoboy", "🛵") if is_delivery
            else ("Pronto para retirada", "Já pode retirar no balcão da Cidade Alta", "🏪"),
            ("Entregue", "Bom apetite com a Don Corleone!", "🍕") if is_delivery
            else ("Retirado", "Bom apetite com a Don Corleone!", "🍕"),
        ]
        timeline = [
            {
                "step": number,
                "label": label,
                "sublabel": sublabel,
                "icon": icon,
                "hora": _hhmm(step_times.get(number)) if number <= current_step else None,
                "completed": number < current_step or (number == current_step == 4),
                "current": number == current_step and not is_cancelled and number < 4,
            }
            for number, (label, sublabel, icon) in enumerate(steps, start=1)
        ]

        cancellation = None
        if is_cancelled:
            entry = order.status_history.filter(status=S.CANCELADO).last()
            cancellation = {
                "motivo": entry.notes if entry else "",
                "hora": _hhmm(entry.created_at) if entry else None,
            }

        items_summary = []
        for it in order.items.all():
            flavors_list = [f.flavor_name_snapshot for f in it.flavors.all()]
            items_summary.append({
                "nome": it.product_name_snapshot,
                "quantidade": it.quantity,
                "subtotal": float(it.subtotal_snapshot),
                "borda": it.crust_name_snapshot if it.crust_name_snapshot != "Sem Borda" else None,
                "sabores": flavors_list
            })

        return Response({
            "codigo": order.readable_code,
            "status": order.status,
            "status_display": "Cancelado" if is_cancelled else steps[current_step - 1][0],
            "is_cancelado": is_cancelled,
            "is_finalizado": is_cancelled or order.status == S.CONCLUIDO,
            "cancelamento": cancellation,
            "previsao": None if is_cancelled else _forecast(order, step_times, current_step),
            "modalidade": order.fulfillment_mode,
            "modalidade_display": order.get_fulfillment_mode_display(),
            "pagamento": order.payment_method,
            "cliente_nome": (order.customer_name or '').split(' ')[0],
            "bairro": order.delivery_neighborhood if is_delivery else "Cidade Alta (Retirada)",
            "total": float(order.total_amount),
            "data_criacao": timezone.localtime(order.created_at).strftime('%d/%m/%Y às %H:%M'),
            "current_step": current_step,
            "timeline": timeline,
            "itens": items_summary
        })
