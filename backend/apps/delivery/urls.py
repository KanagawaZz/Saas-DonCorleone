from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PublicDeliveryConfigView,
    AdminDeliveryZoneViewSet,
    AdminOperatingHourViewSet,
    AdminStoreSettingsView
)

router = DefaultRouter()
router.register(r'admin/zones', AdminDeliveryZoneViewSet, basename='admin-delivery-zone')
router.register(r'admin/hours', AdminOperatingHourViewSet, basename='admin-operating-hour')

urlpatterns = [
    path('config/', PublicDeliveryConfigView.as_view(), name='public-delivery-config'),
    path('admin/settings/', AdminStoreSettingsView.as_view(), name='admin-store-settings'),
    path('', include(router.urls)),
]
