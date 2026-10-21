from django.contrib.auth import views as auth_views
from django.urls import path
from .views import cardapio, dashboard, entregadores, funcionarios, gestao, pedidos, whatsapp

app_name = "painel"

urlpatterns = [
    path("entrar/", auth_views.LoginView.as_view(
        template_name="painel/entrar.html", redirect_authenticated_user=True,
    ), name="entrar"),
    path("sair/", auth_views.LogoutView.as_view(next_page="painel:entrar"), name="sair"),

    path("", dashboard.dashboard, name="dashboard"),

    path("pedidos/", pedidos.quadro, name="pedidos"),
    path("pedidos/quadro/parcial/", pedidos.quadro_parcial, name="pedidos_quadro_parcial"),
    path("pedidos/historico/", pedidos.lista, name="pedidos_historico"),
    path("pedidos/<uuid:pk>/", pedidos.detalhe, name="pedido"),
    path("pedidos/<uuid:pk>/status/", pedidos.mudar_status, name="pedido_status"),

    path("cardapio/", cardapio.lista, name="cardapio"),
    path("cardapio/novo/", cardapio.produto_novo, name="produto_novo"),
    path("cardapio/<uuid:pk>/", cardapio.produto_editar, name="produto"),
    path("cardapio/<uuid:pk>/disponibilidade/", cardapio.alternar_disponibilidade, name="produto_disponibilidade"),
    path("cardapio/bordas/", cardapio.bordas, name="bordas"),
    path("cardapio/categorias/", cardapio.categorias, name="categorias"),

    path("entregas/", gestao.entregas, name="entregas"),
    path("entregadores/", entregadores.entregadores, name="entregadores"),
    path("entregadores/despachar/", entregadores.despachar, name="despachar"),
    path("entregadores/mapa/", entregadores.mapa, name="mapa"),
    path("entregadores/mapa/posicoes/", entregadores.mapa_posicoes, name="mapa_posicoes"),
    path("entregadores/<uuid:pk>/acesso/", entregadores.entregador_acesso, name="entregador_acesso"),
    path("entregadores/<uuid:pk>/", entregadores.entregador, name="entregador"),
    path("entregadores/<uuid:pk>/trabalhando/", entregadores.entregador_trabalhando, name="entregador_trabalhando"),
    path("entregadores/<uuid:pk>/excluir/", entregadores.entregador_excluir, name="entregador_excluir"),
    path("funcionarios/", funcionarios.funcionarios, name="funcionarios"),
    path("funcionarios/<uuid:pk>/", funcionarios.funcionario, name="funcionario"),
    path("funcionarios/<uuid:pk>/excluir/", funcionarios.funcionario_excluir, name="funcionario_excluir"),
    path("funcionarios/vales/<uuid:pk>/excluir/", funcionarios.vale_excluir, name="vale_excluir"),

    path("configuracoes/", gestao.configuracoes, name="configuracoes"),

    path("whatsapp/", whatsapp.whatsapp, name="whatsapp"),
    path("whatsapp/conectar/", whatsapp.whatsapp_conectar, name="whatsapp_conectar"),
    path("whatsapp/estado/", whatsapp.whatsapp_estado, name="whatsapp_estado"),
    path("whatsapp/desconectar/", whatsapp.whatsapp_desconectar, name="whatsapp_desconectar"),
    path("whatsapp/teste/", whatsapp.whatsapp_teste, name="whatsapp_teste"),

    path("clientes/", gestao.clientes, name="clientes"),
    path("clientes/<str:telefone>/", gestao.cliente_detalhe, name="cliente"),
    path("clientes/perfil/<uuid:pk>/vip/", gestao.cliente_alternar_vip, name="cliente_vip"),

    path("promocoes/", gestao.promocoes, name="promocoes"),
    path("promocoes/nova/", gestao.promocao_nova, name="promocao_nova"),
    path("promocoes/<uuid:pk>/", gestao.promocao_editar, name="promocao"),
    path("promocoes/<uuid:pk>/ativa/", gestao.promocao_alternar, name="promocao_ativa"),
]
