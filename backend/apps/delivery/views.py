from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework.permissions import AllowAny, IsAdminUser
from .models import DeliveryZone, OperatingHour, StoreSettings
from .serializers import DeliveryZoneSerializer, OperatingHourSerializer, StoreSettingsSerializer
from apps.tenants.models import Tenant

class PublicDeliveryConfigView(APIView):
    """Returns active delivery zones, schedules and business settings for the frontend."""
    permission_classes = [AllowAny]

    def get(self, request):
        tenant = Tenant.objects.first()
        if not tenant:
            return Response({"bairros": [], "horarios": [], "configuracoes": {}})

        zones = DeliveryZone.objects.filter(tenant=tenant, is_active=True)
        hours = OperatingHour.objects.filter(tenant=tenant)
        settings_obj = getattr(tenant, 'settings', None)

        return Response({
            "bairros": DeliveryZoneSerializer(zones, many=True).data,
            "horarios": OperatingHourSerializer(hours, many=True).data,
            "configuracoes": StoreSettingsSerializer(settings_obj).data if settings_obj else {}
        })

class AdminDeliveryZoneViewSet(viewsets.ModelViewSet):
    """Admin CRUD for delivery neighborhoods and fees."""
    queryset = DeliveryZone.objects.all()
    serializer_class = DeliveryZoneSerializer
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        tenant = Tenant.objects.first()
        serializer.save(tenant=tenant)

class AdminOperatingHourViewSet(viewsets.ModelViewSet):
    """Admin CRUD for store hours."""
    queryset = OperatingHour.objects.all()
    serializer_class = OperatingHourSerializer
    permission_classes = [IsAdminUser]

class AdminStoreSettingsView(APIView):
    """Admin update for store settings."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        tenant = Tenant.objects.first()
        settings_obj, _ = StoreSettings.objects.get_or_create(tenant=tenant)
        return Response(StoreSettingsSerializer(settings_obj).data)

    def put(self, request):
        tenant = Tenant.objects.first()
        settings_obj, _ = StoreSettings.objects.get_or_create(tenant=tenant)
        serializer = StoreSettingsSerializer(settings_obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
