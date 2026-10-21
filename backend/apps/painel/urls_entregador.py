from django.urls import path
from .views import app_entregador

app_name = "entregador"

urlpatterns = [
    path("", app_entregador.app, name="app"),
    path("entrar/<str:token>/", app_entregador.entrar, name="entrar"),
    path("servico/", app_entregador.servico, name="servico"),
    path("pedidos/<uuid:pk>/entregue/", app_entregador.entregue, name="entregue"),
    path("manifest.webmanifest", app_entregador.manifest, name="manifest"),
    path("sw.js", app_entregador.service_worker, name="sw"),
    # Traccar Client "Server URL"
    path("localizacao/", app_entregador.receber_localizacao, name="localizacao"),
]
