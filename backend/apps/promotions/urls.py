from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ActiveBannerPromotionView, ValidateCouponView, AdminPromotionViewSet

router = DefaultRouter()
router.register(r'admin/promotions', AdminPromotionViewSet, basename='admin-promotions')

urlpatterns = [
    path('banner/', ActiveBannerPromotionView.as_view(), name='active-banner-promotion'),
    path('validate/', ValidateCouponView.as_view(), name='validate-coupon'),
    path('', include(router.urls)),
]
