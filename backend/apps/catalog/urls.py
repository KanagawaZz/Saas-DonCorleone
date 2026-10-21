from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PublicCatalogView,
    PublicSiteDataView,
    AdminProductViewSet,
    AdminCategoryViewSet,
    AdminPizzaCrustViewSet,
    ToggleProductAvailabilityView
)

router = DefaultRouter()
router.register(r'admin/products', AdminProductViewSet, basename='admin-product')
router.register(r'admin/categories', AdminCategoryViewSet, basename='admin-category')
router.register(r'admin/crusts', AdminPizzaCrustViewSet, basename='admin-crust')

urlpatterns = [
    # Public catalog endpoint
    path('', PublicCatalogView.as_view(), name='public-catalog'),
    path('site-data/', PublicSiteDataView.as_view(), name='public-site-data'),
    path('toggle-availability/<uuid:pk>/', ToggleProductAvailabilityView.as_view(), name='toggle-availability'),
    path('', include(router.urls)),
]
