from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CreateOrderView, AdminOrderViewSet

router = DefaultRouter()
router.register(r'admin', AdminOrderViewSet, basename='admin-orders')

urlpatterns = [
    path('create/', CreateOrderView.as_view(), name='create-order'),
    path('', include(router.urls)),
]
