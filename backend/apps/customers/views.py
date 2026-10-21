from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from apps.accounts.models import CustomerProfile
from apps.accounts.serializers import UserProfileSerializer

class AdminCustomerViewSet(viewsets.ReadOnlyModelViewSet):
    """Admin management for registered customers, loyalty, order count, and VIP status."""
    queryset = CustomerProfile.objects.select_related('user').all().order_by('-total_spent')
    permission_classes = [IsAdminUser]

    def list(self, request):
        profiles = self.get_queryset()
        data = []
        for p in profiles:
            data.append({
                "id": str(p.id),
                "nome": p.user.get_full_name() or p.user.username,
                "whatsapp": p.whatsapp,
                "bairro": p.default_address_neighborhood,
                "total_pedidos": p.total_orders_count,
                "total_gasto": float(p.total_spent),
                "is_vip": p.is_vip,
                "cadastrado_em": p.created_at.strftime('%d/%m/%Y')
            })
        return Response(data)

    @action(detail=True, methods=['post'], url_path='toggle-vip')
    def toggle_vip(self, request, pk=None):
        profile = self.get_object()
        profile.is_vip = not profile.is_vip
        profile.save(update_fields=['is_vip'])
        return Response({
            "id": str(profile.id),
            "is_vip": profile.is_vip,
            "message": f"Status VIP {'ativado' if profile.is_vip else 'removido'} para {profile.user.get_full_name() or profile.user.username}."
        })
