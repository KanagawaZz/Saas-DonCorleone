from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAdminUser
from .models import Promotion
from .serializers import PromotionSerializer, ValidateCouponSerializer
from apps.tenants.models import Tenant
from django.utils import timezone

class ActiveBannerPromotionView(APIView):
    """Returns currently active top banner promotion for public landing page."""
    permission_classes = [AllowAny]

    def get(self, request):
        today = timezone.localdate()
        promo = Promotion.objects.filter(
            is_active=True,
            show_top_banner=True
        ).first()

        if not promo:
            return Response({"ativa": False})

        valid, _ = promo.is_currently_valid()
        if not valid:
            return Response({"ativa": False})

        return Response({
            "ativa": True,
            "titulo": promo.title,
            "texto": promo.banner_text or promo.description,
            "cupom": promo.coupon_code,
            "tipo": promo.discount_type,
            "desconto": float(promo.discount_value),
            "descontoPercentual": float(promo.discount_value) if promo.discount_type == Promotion.DiscountType.PERCENTAGE else 0
        })

class ValidateCouponView(APIView):
    """Validates coupon code and calculates exact discount."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ValidateCouponSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        code = serializer.validated_data['coupon_code'].strip().upper()
        subtotal = serializer.validated_data['subtotal']

        try:
            promo = Promotion.objects.get(coupon_code__iexact=code, is_active=True)
        except Promotion.DoesNotExist:
            return Response({"valido": False, "mensagem": "Cupom inválido ou inexistente."}, status=status.HTTP_404_NOT_FOUND)

        user = request.user if request.user.is_authenticated else None
        valid, msg = promo.is_currently_valid(user=user, order_subtotal=subtotal)
        if not valid:
            return Response({"valido": False, "mensagem": msg}, status=status.HTTP_400_BAD_REQUEST)

        discount_amount = promo.calculate_discount(subtotal)
        return Response({
            "valido": True,
            "cupom": promo.coupon_code,
            "titulo": promo.title,
            "desconto": float(discount_amount),
            "subtotal_com_desconto": float(max(0, subtotal - discount_amount)),
            "mensagem": f"Cupom '{promo.coupon_code}' aplicado com sucesso! Desconto de R$ {discount_amount:.2f}."
        })

class AdminPromotionViewSet(viewsets.ModelViewSet):
    """Admin CRUD for parameterized promotions."""
    queryset = Promotion.objects.all()
    serializer_class = PromotionSerializer
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        tenant = Tenant.objects.first()
        serializer.save(tenant=tenant)
