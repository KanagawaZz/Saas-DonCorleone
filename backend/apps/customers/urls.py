from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AdminCustomerViewSet

router = DefaultRouter()
router.register(r'admin/customers', AdminCustomerViewSet, basename='admin-customers')

urlpatterns = [
    path('', include(router.urls)),
]
