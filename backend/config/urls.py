"""
URL Configuration for Don Corleone Backend.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='painel:dashboard', permanent=False)),
    path('painel/', include('apps.painel.urls')),
    path('entregador/', include('apps.painel.urls_entregador')),
    path('admin/', admin.site.urls),
    
    # API Version 1
    path('api/v1/accounts/', include('apps.accounts.urls')),
    path('api/v1/catalog/', include('apps.catalog.urls')),
    path('api/v1/customers/', include('apps.customers.urls')),
    path('api/v1/delivery/', include('apps.delivery.urls')),
    path('api/v1/orders/', include('apps.orders.urls')),
    path('api/v1/promotions/', include('apps.promotions.urls')),
    path('api/v1/tracking/', include('apps.tracking.urls')),
    path('api/v1/printing/', include('apps.printing.urls')),
]

# Friendly error pages (HTML) and messages (API), with occurrence code on unexpected errors
handler400 = "apps.core.views.handler400"
handler403 = "apps.core.views.handler403"
handler404 = "apps.core.views.handler404"
handler500 = "apps.core.views.handler500"

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
