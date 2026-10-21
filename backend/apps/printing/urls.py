from django.urls import path
from .views import ThermalReceiptPrintView

urlpatterns = [
    path('<str:code>/', ThermalReceiptPrintView.as_view(), name='thermal-receipt-print'),
]
