from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAdminUser
from .models import Order
from .serializers import CreateOrderSerializer, OrderDetailSerializer
from .services import change_order_status, OrderTransitionError

class CreateOrderView(APIView):
    """
    Public checkout endpoint.
    Validates rules, persists order to database, generates official readable code,
    and returns payload for frontend WhatsApp redirection and confirmation.
    """
    permission_classes = [AllowAny]
    throttle_scope = 'orders'

    def post(self, request):
        serializer = CreateOrderSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            order = serializer.save()
            return Response({
                "success": True,
                "message": "Pedido registrado com sucesso no sistema Don Corleone!",
                "order_id": str(order.id),
                "codigoPedido": order.readable_code,
                "total": float(order.total_amount),
                "tracking_url": order.tracking_url,
                "detalhes": OrderDetailSerializer(order).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AdminOrderViewSet(viewsets.ModelViewSet):
    """Admin and kitchen management for orders, status transitions, and automated WhatsApp."""
    queryset = Order.objects.all().prefetch_related('items__flavors', 'status_history')
    serializer_class = OrderDetailSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        qs = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        return qs

    @action(detail=True, methods=['post'], url_path='update-status')
    def update_status(self, request, pk=None):
        order = self.get_object()
        new_status = request.data.get('status', '').upper()
        notes = request.data.get('notes', '')

        old_status = order.status
        try:
            whatsapp_sent = change_order_status(
                order, new_status, user=request.user, notes=notes, courier_id=request.data.get('courier'),
            )
        except OrderTransitionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "success": True,
            "order_id": str(order.id),
            "readable_code": order.readable_code,
            "old_status": old_status,
            "new_status": new_status,
            "whatsapp_notification_dispatched": whatsapp_sent,
            "message": f"Status do pedido atualizado para {order.get_status_display()} com sucesso!"
        }, status=status.HTTP_200_OK)
