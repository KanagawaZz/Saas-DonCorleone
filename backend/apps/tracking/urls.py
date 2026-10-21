from django.urls import path
from .views import OrderTrackingView

urlpatterns = [
    path('<str:code>/', OrderTrackingView.as_view(), name='order-tracking'),
]
