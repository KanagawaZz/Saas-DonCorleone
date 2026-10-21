"""
Order domain rules shared by the REST API and the owner's panel.
"""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from apps.accounts.models import CustomerProfile
from apps.delivery.models import Employee
from apps.integrations.evolution import (
    send_order_dispatched_notification,
    send_order_ready_pickup_notification,
)
from .models import Order, OrderStatusHistory

S = Order.Status

# Statuses that are still being handled by the kitchen / delivery
OPEN_STATUSES = [S.NOVO, S.CONFIRMADO, S.PREPARO, S.SAIU_PARA_ENTREGA, S.PRONTO_RETIRADA]

_TRANSITIONS = {
    # Confirming an order puts it straight into production
    S.NOVO: [S.PREPARO, S.CANCELADO],
    S.CONFIRMADO: [S.PREPARO, S.CANCELADO],
    S.PREPARO: [S.SAIU_PARA_ENTREGA, S.PRONTO_RETIRADA, S.CANCELADO],
    S.SAIU_PARA_ENTREGA: [S.CONCLUIDO, S.CANCELADO],
    S.PRONTO_RETIRADA: [S.CONCLUIDO, S.CANCELADO],
    S.CONCLUIDO: [],
    S.CANCELADO: [],
}

# Short labels for the action buttons
ACTION_LABELS = {
    S.PREPARO: "Confirmar",
    S.SAIU_PARA_ENTREGA: "Saiu para entrega",
    S.PRONTO_RETIRADA: "Pronto p/ retirada",
    S.CONCLUIDO: "Concluir",
    S.CANCELADO: "Cancelar",
}


class OrderTransitionError(ValueError):
    """Raised when a status change is not allowed."""


def allowed_next_statuses(order: Order) -> list[str]:
    """Next statuses for the order, respecting delivery vs pickup."""
    next_statuses = list(_TRANSITIONS.get(order.status, []))
    if order.fulfillment_mode == Order.FulfillmentMode.DELIVERY:
        next_statuses = [s for s in next_statuses if s != S.PRONTO_RETIRADA]
    else:
        next_statuses = [s for s in next_statuses if s != S.SAIU_PARA_ENTREGA]
    return next_statuses


def _dispatch_courier(order: Order, courier_id):
    """
    Courier taking the order out. Required once the store has riders registered,
    and it must be someone marked as working today.
    """
    couriers = Employee.objects.filter(tenant_id=order.tenant_id, role=Employee.Role.COURIER, is_active=True)
    if not courier_id:
        if couriers.exists():
            raise OrderTransitionError("Escolha o entregador que vai levar o pedido.")
        return None
    try:
        courier = couriers.filter(pk=courier_id).first()
    except (ValidationError, ValueError):
        courier = None
    if not courier:
        raise OrderTransitionError("Entregador não encontrado.")
    if not courier.is_working_today:
        raise OrderTransitionError(f"{courier.name} não está marcado como trabalhando hoje.")
    return courier


def change_order_status(order: Order, new_status: str, user=None, notes: str = "", courier_id=None) -> bool:
    """
    Moves the order to new_status, records the audit history, updates the customer's
    totals when the order is completed and notifies the customer on WhatsApp.
    Going out for delivery records the courier (courier_id).
    Returns whether a WhatsApp notification was sent.
    """
    new_status = (new_status or "").upper()
    if new_status not in allowed_next_statuses(order):
        raise OrderTransitionError(
            f"Não é possível mudar de {order.get_status_display()} para {new_status or 'vazio'}."
        )
    if new_status == S.CANCELADO and not notes.strip():
        raise OrderTransitionError("Informe o motivo do cancelamento.")
    courier = _dispatch_courier(order, courier_id) if new_status == S.SAIU_PARA_ENTREGA else None

    old_status = order.status
    with transaction.atomic():
        order.status = new_status
        fields = ["status", "updated_at"]
        if courier:
            order.courier = courier
            fields.append("courier")
        order.save(update_fields=fields)
        default_note = (
            "Pedido confirmado pela pizzaria e enviado para preparo"
            if old_status == S.NOVO and new_status == S.PREPARO
            else f"Saiu para entrega com {courier.name}"
            if courier
            else f"Status alterado de {old_status} para {new_status}"
        )
        OrderStatusHistory.objects.create(
            order=order,
            status=new_status,
            notes=(notes.strip() or default_note)[:255],
            changed_by=user if user and user.is_authenticated else None,
        )
        if new_status == S.CONCLUIDO and order.customer_user_id:
            CustomerProfile.objects.filter(user_id=order.customer_user_id).update(
                total_orders_count=F("total_orders_count") + 1,
                total_spent=F("total_spent") + order.total_amount,
            )

    if new_status == S.SAIU_PARA_ENTREGA:
        return send_order_dispatched_notification(order)
    if new_status == S.PRONTO_RETIRADA:
        return send_order_ready_pickup_notification(order)
    return False
