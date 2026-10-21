from datetime import timedelta
from decimal import Decimal
from io import StringIO
from unittest import mock
from urllib.parse import parse_qs, urlsplit
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import CustomerProfile, User
from apps.catalog.models import Product
from apps.delivery.models import CourierLocation, DeliveryZone, Employee, OperatingHour, SalaryAdvance, StoreSettings
from apps.orders.models import Order, OrderStatusHistory
from apps.promotions.models import Promotion
from apps.tenants.models import Tenant


# Tests never talk to a real Evolution API, even when the developer's .env has a key
@override_settings(EVOLUTION_API_KEY="")
class PainelTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("import_legacy_data", stdout=StringIO())
        OperatingHour.objects.update(opening_time="00:00", closing_time="23:59", is_active=True)
        cls.tenant = Tenant.objects.get()
        cls.staff = User.objects.create_user(username="dono", password="senha-forte-123", is_staff=True, tenant=cls.tenant)

    def setUp(self):
        cache.clear()
        self.client.force_login(self.staff)

    def create_order(self, **overrides):
        api = APIClient()
        body = {
            "cliente": {"nome": "Maria Silva", "telefone": "(65) 99999-0000"},
            "modalidade": "entrega",
            "endereco": {"logradouro": "Rua A", "numero": "1", "bairro": "Cidade Alta"},
            "pagamento": {"forma": "pix"},
            "itens": [{"tipo": "pizza", "tamanho": {"id": "grande"}, "sabores": [{"id": "pizza-calabresa"}]}],
            **overrides,
        }
        res = api.post("/api/v1/orders/create/", body, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        return Order.objects.get(readable_code=res.data["codigoPedido"])


class AccessTests(PainelTestCase):
    def test_anonymous_is_sent_to_login(self):
        self.client.logout()
        res = self.client.get(reverse("painel:dashboard"))
        self.assertRedirects(res, f"{reverse('painel:entrar')}?next={reverse('painel:dashboard')}")

    def test_customer_account_cannot_open_the_panel(self):
        customer = User.objects.create_user(username="65988887777", password="senha-forte-123")
        self.client.force_login(customer)
        self.assertEqual(self.client.get(reverse("painel:dashboard")).status_code, 403)

    def test_login_page_and_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("painel:entrar")).status_code, 200)
        res = self.client.post(reverse("painel:entrar"), {"username": "dono", "password": "senha-forte-123"})
        self.assertRedirects(res, reverse("painel:dashboard"))

    def test_root_redirects_to_panel(self):
        self.assertRedirects(self.client.get("/"), reverse("painel:dashboard"))


class PagesRenderTests(PainelTestCase):
    def test_every_page_renders(self):
        order = self.create_order()
        product = Product.objects.get(slug="pizza-calabresa")
        promo = Promotion.objects.create(tenant=self.tenant, title="Terça", coupon_code="TERCA10", discount_value=10)
        pages = [
            reverse("painel:dashboard"),
            reverse("painel:dashboard") + "?periodo=30d",
            reverse("painel:pedidos"),
            reverse("painel:pedidos_quadro_parcial"),
            reverse("painel:pedidos_historico") + "?busca=Maria&status=NOVO&de=2020-01-01&ate=2099-01-01",
            reverse("painel:pedido", args=[order.pk]),
            reverse("painel:cardapio"),
            reverse("painel:cardapio") + "?esgotados=1&busca=calabresa",
            reverse("painel:produto_novo"),
            reverse("painel:produto", args=[product.pk]),
            reverse("painel:bordas"),
            reverse("painel:categorias"),
            reverse("painel:entregas"),
            reverse("painel:entregadores"),
            reverse("painel:entregadores") + "?dia=2026-01-31",
            reverse("painel:funcionarios"),
            reverse("painel:funcionarios") + "?mes=2026-01",
            reverse("painel:funcionarios") + "?mes=invalido",
            reverse("painel:configuracoes"),
            reverse("painel:clientes"),
            reverse("painel:clientes") + "?aba=vip",
            reverse("painel:cliente", args=[order.customer_phone]),
            reverse("painel:promocoes"),
            reverse("painel:promocao_nova"),
            reverse("painel:promocao", args=[promo.pk]),
        ]
        for url in pages:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_board_shows_open_orders(self):
        order = self.create_order()
        res = self.client.get(reverse("painel:pedidos_quadro_parcial"))
        self.assertContains(res, order.readable_code)
        self.assertContains(res, "Confirmar")


class OrderStatusTests(PainelTestCase):
    def change(self, order, status, motivo=""):
        return self.client.post(reverse("painel:pedido_status", args=[order.pk]), {"status": status, "motivo": motivo})

    def test_full_delivery_flow_and_customer_totals(self):
        customer = User.objects.create_user(username="65999990000", password="senha-forte-123")
        CustomerProfile.objects.create(user=customer, tenant=self.tenant, whatsapp="65999990000")
        api = APIClient()
        api.force_authenticate(customer)
        res = api.post("/api/v1/orders/create/", {
            "cliente": {"nome": "Maria", "telefone": "65999990000"}, "modalidade": "entrega",
            "endereco": {"bairro": "Cidade Alta"}, "pagamento": {"forma": "pix"},
            "itens": [{"tipo": "pizza", "tamanho": {"id": "grande"}, "sabores": [{"id": "pizza-calabresa"}]}],
        }, format="json")
        order = Order.objects.get(readable_code=res.data["codigoPedido"])

        # "Confirmar" moves the order straight to PREPARO
        for status in ["PREPARO", "SAIU_PARA_ENTREGA", "CONCLUIDO"]:
            self.change(order, status)
            order.refresh_from_db()
            self.assertEqual(order.status, status)
        self.assertEqual(order.status_history.count(), 4)
        self.assertIn("confirmado pela pizzaria", order.status_history.all()[1].notes)
        self.assertEqual(order.status_history.last().changed_by, self.staff)
        profile = CustomerProfile.objects.get(user=customer)
        self.assertEqual(profile.total_orders_count, 1)
        self.assertEqual(profile.total_spent, order.total_amount)

    def test_invalid_jump_is_blocked(self):
        order = self.create_order()
        self.change(order, "CONCLUIDO")
        order.refresh_from_db()
        self.assertEqual(order.status, "NOVO")

    def test_confirmed_step_is_no_longer_used(self):
        order = self.create_order()
        self.change(order, "CONFIRMADO")
        order.refresh_from_db()
        self.assertEqual(order.status, "NOVO")

    def test_pickup_order_cannot_go_out_for_delivery(self):
        order = self.create_order(modalidade="retirada")
        self.change(order, "PREPARO")
        self.change(order, "SAIU_PARA_ENTREGA")
        order.refresh_from_db()
        self.assertEqual(order.status, "PREPARO")

    def test_cancel_requires_reason(self):
        order = self.create_order()
        self.change(order, "CANCELADO")
        order.refresh_from_db()
        self.assertEqual(order.status, "NOVO")
        self.change(order, "CANCELADO", motivo="Cliente desistiu")
        order.refresh_from_db()
        self.assertEqual(order.status, "CANCELADO")
        self.assertEqual(OrderStatusHistory.objects.filter(order=order).last().notes, "Cliente desistiu")

    def test_api_uses_the_same_transition_rules(self):
        order = self.create_order()
        api = APIClient()
        api.force_authenticate(self.staff)
        res = api.post(f"/api/v1/orders/admin/{order.pk}/update-status/", {"status": "CONCLUIDO"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_get_does_not_change_status(self):
        order = self.create_order()
        self.assertEqual(self.client.get(reverse("painel:pedido_status", args=[order.pk])).status_code, 405)


class MenuManagementTests(PainelTestCase):
    def test_sold_out_product_disappears_from_site_and_checkout(self):
        product = Product.objects.get(slug="pizza-calabresa")
        self.client.post(reverse("painel:produto_disponibilidade", args=[product.pk]))
        product.refresh_from_db()
        self.assertFalse(product.is_available)

        data = APIClient().get("/api/v1/catalog/site-data/").json()
        ids = [i["id"] for c in data["cardapio"]["categorias"] for i in c["itens"]]
        self.assertNotIn("pizza-calabresa", ids)
        self.assertIn("pizza-mussarela", ids)

    def test_editing_pizza_prices_changes_site_and_order_price(self):
        product = Product.objects.get(slug="pizza-calabresa")
        sizes = list(product.size_prices.order_by("price"))
        post = {
            "name": product.name, "category": product.category_id, "product_type": "pizza",
            "price_category": "tradicional", "description": product.description, "base_price": "",
            "price_text": "A partir de R$ 50,00", "tag": "", "display_order": 1, "is_available": "on",
            "photo_url": product.photo_url,
            "tamanhos-TOTAL_FORMS": "3", "tamanhos-INITIAL_FORMS": "3",
            "tamanhos-MIN_NUM_FORMS": "0", "tamanhos-MAX_NUM_FORMS": "1000",
        }
        for i, size in enumerate(sizes):
            post.update({
                f"tamanhos-{i}-id": size.pk, f"tamanhos-{i}-size_id": size.size_id,
                f"tamanhos-{i}-size_name": size.size_name, f"tamanhos-{i}-slices": size.slices,
                f"tamanhos-{i}-max_flavors": size.max_flavors,
                f"tamanhos-{i}-price": "80.00" if size.size_id == "grande" else size.price,
            })
        res = self.client.post(reverse("painel:produto", args=[product.pk]), post)
        self.assertRedirects(res, reverse("painel:cardapio"))

        data = APIClient().get("/api/v1/catalog/site-data/").json()
        item = next(i for c in data["cardapio"]["categorias"] for i in c["itens"] if i["id"] == "pizza-calabresa")
        self.assertEqual(item["precos"]["grande"], 80.0)
        self.assertEqual(self.create_order().total_amount, Decimal("85.00"))  # 80 + R$ 5 delivery

    def test_create_simple_product(self):
        category = Product.objects.get(slug="esfiha-carne").category
        res = self.client.post(reverse("painel:produto_novo"), {
            "name": "Esfiha de Costela", "category": category.pk, "product_type": "simple",
            "price_category": "tradicional", "base_price": "9.50", "display_order": 99, "is_available": "on",
            "tamanhos-TOTAL_FORMS": "0", "tamanhos-INITIAL_FORMS": "0",
            "tamanhos-MIN_NUM_FORMS": "0", "tamanhos-MAX_NUM_FORMS": "1000",
        })
        self.assertRedirects(res, reverse("painel:cardapio"))
        product = Product.objects.get(slug="esfiha-de-costela")
        self.assertEqual(product.price_text, "R$ 9,50")
        self.assertEqual(product.tenant, self.tenant)

    def test_negative_price_is_rejected(self):
        product = Product.objects.get(slug="esfiha-carne")
        res = self.client.post(reverse("painel:produto", args=[product.pk]), {
            "name": product.name, "category": product.category_id, "product_type": "simple",
            "price_category": "tradicional", "base_price": "-1", "display_order": 1,
            "tamanhos-TOTAL_FORMS": "0", "tamanhos-INITIAL_FORMS": "0",
            "tamanhos-MIN_NUM_FORMS": "0", "tamanhos-MAX_NUM_FORMS": "1000",
        })
        self.assertEqual(res.status_code, 200)
        product.refresh_from_db()
        self.assertEqual(product.base_price, Decimal("6.50"))


class DeliveryAndSettingsTests(PainelTestCase):
    def test_edit_fee_and_add_neighborhood(self):
        zones = list(DeliveryZone.objects.filter(tenant=self.tenant).order_by("city", "neighborhood"))
        post = {
            "bairros-TOTAL_FORMS": str(len(zones) + 1), "bairros-INITIAL_FORMS": str(len(zones)),
            "bairros-MIN_NUM_FORMS": "0", "bairros-MAX_NUM_FORMS": "1000",
        }
        for i, z in enumerate(zones):
            post.update({
                f"bairros-{i}-id": z.pk, f"bairros-{i}-neighborhood": z.neighborhood, f"bairros-{i}-city": z.city,
                f"bairros-{i}-fee": "7.00" if z.neighborhood == "Cidade Alta" else z.fee,
                f"bairros-{i}-estimated_minutes": z.estimated_minutes, f"bairros-{i}-is_active": "on",
            })
        n = len(zones)
        post.update({
            f"bairros-{n}-neighborhood": "Jardim Novo", f"bairros-{n}-city": "Cuiabá",
            f"bairros-{n}-fee": "12.00", f"bairros-{n}-estimated_minutes": "60", f"bairros-{n}-is_active": "on",
        })
        self.assertEqual(self.client.post(reverse("painel:entregas"), post).status_code, 302)
        self.assertEqual(DeliveryZone.objects.get(neighborhood="Cidade Alta").fee, Decimal("7.00"))
        self.assertEqual(DeliveryZone.objects.get(neighborhood="Jardim Novo").tenant, self.tenant)

        data = APIClient().get("/api/v1/catalog/site-data/").json()
        self.assertIn({"cidade": "Cuiabá", "bairro": "Jardim Novo", "taxa": 12.0}, data["bairros"])

    def settings_post(self, **changes):
        store = StoreSettings.objects.get(tenant=self.tenant)
        hours = list(OperatingHour.objects.filter(tenant=self.tenant).order_by("weekday"))
        post = {
            "minimum_order": store.minimum_order, "delivery_time_text": store.delivery_time_text,
            "pickup_time_text": store.pickup_time_text, "pix_key": store.pix_key, "pix_type": store.pix_type,
            "pix_holder": store.pix_holder, "pix_instructions": store.pix_instructions,
            "emergency_closed_reason": "",
            "horarios-TOTAL_FORMS": "7", "horarios-INITIAL_FORMS": "7",
            "horarios-MIN_NUM_FORMS": "0", "horarios-MAX_NUM_FORMS": "1000",
        }
        for i, h in enumerate(hours):
            post.update({
                f"horarios-{i}-id": h.pk, f"horarios-{i}-opening_time": "00:00",
                f"horarios-{i}-closing_time": "23:59", f"horarios-{i}-cutoff_time": "23:45",
                f"horarios-{i}-is_active": "on",
            })
        post.update(changes)
        return self.client.post(reverse("painel:configuracoes"), post)

    def test_emergency_close_blocks_checkout_and_shows_closed_on_site(self):
        self.assertEqual(self.settings_post(emergency_closed="on", emergency_closed_reason="Chuva forte").status_code, 302)
        res = APIClient().post("/api/v1/orders/create/", {
            "cliente": {"nome": "Ana", "telefone": "65999990000"}, "modalidade": "retirada", "pagamento": {"forma": "pix"},
            "itens": [{"tipo": "pizza", "tamanho": {"id": "grande"}, "sabores": [{"id": "pizza-calabresa"}]}],
        }, format="json")
        self.assertEqual(res.status_code, 400)
        data = APIClient().get("/api/v1/catalog/site-data/").json()
        self.assertTrue(data["fechamentoEmergencial"]["ativo"])
        self.assertTrue(any(d["abertura"] == "00:00" and d["fechamento"] == "00:00" for d in data["horario"]["dias"]))

    def test_minimum_order_change_reaches_the_site(self):
        self.assertEqual(self.settings_post(minimum_order="30.00").status_code, 302)
        data = APIClient().get("/api/v1/catalog/site-data/").json()
        self.assertEqual(data["pagamento"]["pedidoMinimo"], 30.0)

    def test_invalid_hours_are_rejected(self):
        res = self.settings_post(**{"horarios-0-closing_time": "10:00", "horarios-0-opening_time": "18:00"})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "O fechamento precisa ser depois da abertura.")


class CourierTests(PainelTestCase):
    def setUp(self):
        super().setUp()
        today = timezone.localdate()
        self.joao = Employee.objects.create(tenant=self.tenant, name="João", working_on=today)
        self.pedro = Employee.objects.create(tenant=self.tenant, name="Pedro", working_on=today)

    def ready_order(self, **overrides):
        order = self.create_order(**overrides)
        self.client.post(reverse("painel:pedido_status", args=[order.pk]), {"status": "PREPARO"})
        return order

    def dispatch(self, order, courier):
        return self.client.post(reverse("painel:pedido_status", args=[order.pk]), {
            "status": "SAIU_PARA_ENTREGA", "entregador": courier.pk if courier else "",
        })

    def complete(self, order):
        self.client.post(reverse("painel:pedido_status", args=[order.pk]), {"status": "CONCLUIDO"})

    def test_going_out_requires_a_courier_once_riders_are_registered(self):
        order = self.ready_order()
        self.dispatch(order, None)
        order.refresh_from_db()
        self.assertEqual(order.status, "PREPARO")

        self.dispatch(order, self.joao)
        order.refresh_from_db()
        self.assertEqual((order.status, order.courier), ("SAIU_PARA_ENTREGA", self.joao))
        self.assertEqual(order.status_history.last().notes, "Saiu para entrega com João")

    def test_courier_must_be_working_today(self):
        self.pedro.working_on = timezone.localdate() - timedelta(days=1)
        self.pedro.save()
        order = self.ready_order()
        self.dispatch(order, self.pedro)
        order.refresh_from_db()
        self.assertEqual(order.status, "PREPARO")

    def test_bag_dispatches_several_orders_with_the_same_courier(self):
        orders = [self.ready_order() for _ in range(3)]
        pickup = self.ready_order(modalidade="retirada")
        res = self.client.post(reverse("painel:despachar"), {
            "pedidos": [o.pk for o in orders] + [pickup.pk], "entregador": self.joao.pk,
        })
        self.assertRedirects(res, reverse("painel:entregadores"), fetch_redirect_response=False)
        self.assertEqual(Order.objects.filter(courier=self.joao, status="SAIU_PARA_ENTREGA").count(), 3)
        pickup.refresh_from_db()
        self.assertEqual(pickup.status, "PREPARO")

    def test_page_sums_delivered_orders_and_fees_per_courier(self):
        delivered = [self.ready_order() for _ in range(2)]
        on_route = self.ready_order()
        cancelled = self.ready_order()
        for order in delivered + [on_route, cancelled]:
            self.dispatch(order, self.joao)
        for order in delivered:
            self.complete(order)
        self.client.post(reverse("painel:pedido_status", args=[cancelled.pk]), {"status": "CANCELADO", "motivo": "Cliente sumiu"})
        other = self.ready_order(endereco={"bairro": "Bairro Inexistente"})
        self.dispatch(other, self.pedro)
        self.complete(other)

        res = self.client.get(reverse("painel:entregadores"))
        rows = {r["entregador"].name: r for r in res.context["linhas"]}
        self.assertEqual((rows["João"]["qtd"], rows["João"]["taxas"], rows["João"]["em_rota"]), (2, Decimal("10.00"), 1))
        self.assertEqual((rows["Pedro"]["qtd"], rows["Pedro"]["taxas"]), (1, Decimal("0.00")))
        self.assertEqual(res.context["total_taxas"], Decimal("10.00"))
        sheet = {c["entregador"].name: c for c in res.context["planilha"]}
        self.assertEqual(len(sheet["João"]["pedidos"]), 3)  # 2 delivered + 1 still in the bag, cancelled left out
        self.assertEqual(sheet["João"]["a_cobrar"], 0)  # PIX orders show "pg"

        cash = self.ready_order(pagamento={"forma": "dinheiro", "trocoPara": 100})
        self.dispatch(cash, self.pedro)
        sheet = {c["entregador"].name: c for c in self.client.get(reverse("painel:entregadores")).context["planilha"]}
        self.assertEqual(sheet["Pedro"]["a_cobrar"], cash.total_amount)

        detail = self.client.get(reverse("painel:entregador", args=[self.joao.pk]))
        self.assertEqual(len(detail.context["entregues"]), 2)
        self.assertIsNotNone(detail.context["entregues"][0].saiu_em)

        yesterday = (timezone.localdate() - timedelta(days=1)).isoformat()
        self.assertEqual(self.client.get(reverse("painel:entregadores") + f"?dia={yesterday}").context["qtd_entregas"], 0)

    def test_working_flag_toggles_and_resets_the_next_day(self):
        self.client.post(reverse("painel:entregador_trabalhando", args=[self.joao.pk]))
        self.joao.refresh_from_db()
        self.assertFalse(self.joao.is_working_today)
        self.client.post(reverse("painel:entregador_trabalhando", args=[self.joao.pk]))
        self.joao.refresh_from_db()
        self.assertTrue(self.joao.is_working_today)
        with mock.patch("django.utils.timezone.localdate", return_value=timezone.localdate() + timedelta(days=1)):
            self.assertFalse(self.joao.is_working_today)

    def test_register_and_remove_courier(self):
        res = self.client.post(reverse("painel:entregadores"), {"name": "  Ana   Lima ", "phone": "(65) 98888-7777"})
        self.assertRedirects(res, reverse("painel:entregadores"))
        ana = Employee.objects.get(name="Ana Lima")
        self.assertEqual((ana.phone, ana.tenant, ana.is_working_today), ("65988887777", self.tenant, True))
        self.assertEqual(self.client.post(reverse("painel:entregadores"), {"name": "ana lima"}).status_code, 200)

        self.client.post(reverse("painel:entregador_excluir", args=[ana.pk]))
        self.assertFalse(Employee.objects.filter(pk=ana.pk).exists())

    def test_courier_with_deliveries_is_kept(self):
        order = self.ready_order()
        self.dispatch(order, self.joao)
        self.client.post(reverse("painel:entregador_excluir", args=[self.joao.pk]))
        self.assertTrue(Employee.objects.filter(pk=self.joao.pk).exists())

    def test_board_offers_the_couriers_working_today(self):
        Employee.objects.create(tenant=self.tenant, name="Carla Cozinha", role="cozinha", working_on=timezone.localdate())
        self.ready_order()
        res = self.client.get(reverse("painel:pedidos_quadro_parcial"))
        self.assertContains(res, "Quem vai levar?")
        self.assertContains(res, "Pedro")
        self.assertNotContains(res, "Carla Cozinha")

    def test_courier_who_left_the_team_cannot_take_orders(self):
        Employee.objects.filter(pk=self.pedro.pk).update(is_active=False)
        order = self.ready_order()
        self.dispatch(order, self.pedro)
        order.refresh_from_db()
        self.assertEqual(order.status, "PREPARO")


class CourierAppTests(PainelTestCase):
    def setUp(self):
        super().setUp()
        self.joao = Employee.objects.create(tenant=self.tenant, name="João Silva", phone="65988887777", working_on=timezone.localdate())
        self.token = self.joao.new_access_token()

    def send_position(self, **overrides):
        data = {"id": self.token, "lat": "-15.6010", "lon": "-56.0970", "timestamp": str(int(timezone.now().timestamp())),
                "accuracy": "8.5", "batt": "76.0", "speed": "10.5", **overrides}
        res = Client().post(reverse("entregador:localizacao"), data)  # Traccar: form POST, no session/CSRF
        self.assertEqual(res.status_code, 200)
        return CourierLocation.objects.filter(courier=self.joao).first()

    def dispatched_order(self, **overrides):
        order = self.create_order(**overrides)
        self.client.post(reverse("painel:pedido_status", args=[order.pk]), {"status": "PREPARO"})
        self.client.post(reverse("painel:pedido_status", args=[order.pk]), {"status": "SAIU_PARA_ENTREGA", "entregador": self.joao.pk})
        order.refresh_from_db()
        return order

    def courier_client(self):
        client = Client()
        client.get(reverse("entregador:entrar", args=[self.token]))
        return client

    def test_traccar_position_is_stored(self):
        location = self.send_position()
        self.assertEqual((float(location.latitude), float(location.longitude), location.battery), (-15.601, -56.097, 76))

        res = self.client.get(reverse("painel:mapa_posicoes"))
        courier = res.json()["entregadores"][0]
        self.assertEqual((courier["nome"], courier["iniciais"], courier["lat"], courier["parado"]), ("João Silva", "JS", -15.601, False))

        # Traccar goes quiet while the phone is still: the last position stays, shown as stopped
        CourierLocation.objects.update(recorded_at=timezone.now() - timedelta(minutes=40))
        courier = self.client.get(reverse("painel:mapa_posicoes")).json()["entregadores"][0]
        self.assertEqual((courier["lat"], courier["parado"]), (-15.601, True))

    def test_positions_are_ignored_off_duty_and_with_bad_data(self):
        self.assertIsNone(self.send_position(id="codigo-errado"))
        self.assertIsNone(self.send_position(lat="abc"))
        self.assertIsNone(self.send_position(lat="0", lon="0"))
        self.assertIsNone(self.send_position(timestamp=str(int(timezone.now().timestamp()) - 3600)))  # buffered, too old
        Employee.objects.filter(pk=self.joao.pk).update(working_on=None)
        self.assertIsNone(self.send_position())

    def test_outside_store_hours_only_with_an_order_in_the_bag(self):
        OperatingHour.objects.update(is_active=False)
        self.assertIsNone(self.send_position())
        OperatingHour.objects.update(is_active=True)
        self.dispatched_order()
        OperatingHour.objects.update(is_active=False)
        self.assertIsNotNone(self.send_position())

    def test_older_positions_never_overwrite_newer_ones(self):
        now = int(timezone.now().timestamp())
        self.send_position(timestamp=str(now), lat="-15.6")
        location = self.send_position(timestamp=str((now - 60) * 1000), lat="-15.7")  # milliseconds, older
        self.assertEqual(float(location.latitude), -15.6)

    def test_link_opens_the_app_and_renewing_revokes_it(self):
        client = self.courier_client()
        self.assertContains(client.get(reverse("entregador:app")), "Olá, João Silva")
        self.assertIn(self.token, client.get(reverse("entregador:manifest")).json()["start_url"])

        self.client.post(reverse("painel:entregador_acesso", args=[self.joao.pk]), {"acao": "gerar"})
        self.assertEqual(client.get(reverse("entregador:app")).status_code, 403)
        self.assertEqual(Client().get(reverse("entregador:entrar", args=[self.token])).status_code, 403)

    def test_app_shows_the_bag_with_route_and_what_to_collect(self):
        order = self.dispatched_order(pagamento={"forma": "dinheiro", "trocoPara": 100},
                                      endereco={"logradouro": "Rua das Flores", "numero": "12", "bairro": "Cidade Alta"})
        res = self.courier_client().get(reverse("entregador:app"))
        self.assertContains(res, f"#{order.readable_code}")
        self.assertContains(res, "Cobrar")
        self.assertContains(res, "https://www.google.com/maps/dir/?api=1&amp;travelmode=driving&amp;destination=Rua%20das%20Flores%2C%2012%2C%20Cidade%20Alta")
        self.assertContains(res, "waze.com/ul")

    def test_courier_marks_own_order_delivered_and_it_counts(self):
        order = self.dispatched_order()
        client = self.courier_client()
        client.post(reverse("entregador:entregue", args=[order.pk]))
        order.refresh_from_db()
        self.assertEqual(order.status, "CONCLUIDO")
        self.assertEqual(client.get(reverse("entregador:app")).context["taxas_hoje"], order.delivery_fee)

    def test_courier_cannot_touch_someone_elses_order(self):
        maria = Employee.objects.create(tenant=self.tenant, name="Maria", working_on=timezone.localdate())
        order = self.create_order()
        self.client.post(reverse("painel:pedido_status", args=[order.pk]), {"status": "PREPARO"})
        self.client.post(reverse("painel:pedido_status", args=[order.pk]), {"status": "SAIU_PARA_ENTREGA", "entregador": maria.pk})
        self.assertEqual(self.courier_client().post(reverse("entregador:entregue", args=[order.pk])).status_code, 404)

    def test_setup_steps_only_until_traccar_first_connects(self):
        client = self.courier_client()
        self.assertContains(client.get(reverse("entregador:app")), "1. Configurar o Traccar")

        self.send_position()
        self.joao.refresh_from_db()
        self.assertIsNotNone(self.joao.traccar_connected_at)

        # Next day: the position was deleted when the shift ended, but Traccar is still set up
        client.post(reverse("entregador:servico"))
        client.post(reverse("entregador:servico"))
        res = client.get(reverse("entregador:app"))
        self.assertNotContains(res, "1. Configurar o Traccar")
        self.assertContains(res, "Ligar o rastreamento no Traccar")

        # A new link means a new code: Traccar has to be set up again
        self.client.post(reverse("painel:entregador_acesso", args=[self.joao.pk]), {"acao": "gerar"})
        self.joao.refresh_from_db()
        self.assertIsNone(self.joao.traccar_connected_at)

    def test_ending_the_shift_forgets_the_position(self):
        self.send_position()
        client = self.courier_client()
        order = self.dispatched_order()
        client.post(reverse("entregador:servico"))  # blocked: still has an order in the bag
        self.joao.refresh_from_db()
        self.assertTrue(self.joao.is_working_today)

        client.post(reverse("entregador:entregue", args=[order.pk]))
        client.post(reverse("entregador:servico"))
        self.joao.refresh_from_db()
        self.assertFalse(self.joao.is_working_today)
        self.assertFalse(CourierLocation.objects.exists())

    def test_manager_pages_render(self):
        for url in [reverse("painel:mapa"), reverse("painel:entregador", args=[self.joao.pk])]:
            self.assertEqual(self.client.get(url).status_code, 200)
        self.assertContains(self.client.get(reverse("painel:entregador", args=[self.joao.pk])), self.token)
        # Same section on the staff page, reached from "Funcionários e vales"
        self.assertContains(self.client.get(reverse("painel:funcionario", args=[self.joao.pk])), "App do entregador e localização")

    def test_traccar_qr_and_config_link_follow_the_app_format(self):
        page = self.client.get(reverse("painel:entregador", args=[self.joao.pk]))
        # QR scanned inside Traccar: origin + path become the server URL, the query sets the rest
        qr = urlsplit(page.context["traccar_qr"])
        self.assertEqual(f"{qr.scheme}://{qr.netloc}{qr.path}", "http://testserver/entregador/localizacao/")
        self.assertEqual(parse_qs(qr.query), {"id": [self.token], "accuracy": ["high"], "distance": ["50"],
                                              "interval": ["120"], "buffer": ["true"], "stop_detection": ["true"]})
        self.assertContains(page, "data-qr=")

        app = self.courier_client().get(reverse("entregador:app"))
        self.assertContains(app, "1. Configurar o Traccar")  # on duty and no position yet: setup steps on top
        self.assertContains(app, "org.traccar.client://action/start")
        link = urlsplit(app.context["traccar_config_link"])
        self.assertEqual(link.scheme, "org.traccar.client")
        self.assertEqual(parse_qs(link.query)["url"], ["http://testserver/entregador/localizacao/"])
        self.assertEqual(parse_qs(link.query)["id"], [self.token])
        self.assertEqual(Client().get(reverse("painel:mapa_posicoes")).status_code, 302)  # staff only

    @mock.patch("apps.integrations.evolution.send_whatsapp_message", return_value=True)
    @mock.patch("apps.integrations.evolution.is_configured", return_value=True)
    def test_link_is_sent_on_whatsapp(self, configured, send):
        self.client.post(reverse("painel:entregador_acesso", args=[self.joao.pk]), {"acao": "enviar"})
        phone, text, _instance = send.call_args.args
        self.assertEqual(phone, "65988887777")
        self.assertIn(f"/entregador/entrar/{self.token}/", text)


class StaffAdvanceTests(PainelTestCase):
    def setUp(self):
        super().setUp()
        self.ana = Employee.objects.create(tenant=self.tenant, name="Ana", role="cozinha")
        self.joao = Employee.objects.create(tenant=self.tenant, name="João", role="entregador")

    def add_advance(self, employee, amount, day=None):
        return self.client.post(reverse("painel:funcionarios"), {
            "acao": "vale", "employee": employee.pk, "amount": amount,
            "date": (day or timezone.localdate()).isoformat(), "notes": "",
        })

    def test_monthly_totals_per_employee(self):
        today = timezone.localdate()
        self.add_advance(self.ana, "50.00")
        self.add_advance(self.ana, "30.00")
        self.add_advance(self.joao, "13.00")
        last_month = today.replace(day=1) - timedelta(days=1)
        self.add_advance(self.ana, "100.00", day=last_month)

        res = self.client.get(reverse("painel:funcionarios"))
        rows = {r["funcionario"].name: r for r in res.context["linhas"]}
        self.assertEqual((rows["Ana"]["qtd"], rows["Ana"]["total"]), (2, Decimal("80.00")))
        self.assertEqual(rows["João"]["total"], Decimal("13.00"))
        self.assertEqual(res.context["total_mes"], Decimal("93.00"))
        self.assertEqual(SalaryAdvance.objects.filter(employee=self.ana).first().created_by, self.staff)

        old = self.client.get(reverse("painel:funcionarios") + f"?mes={last_month:%Y-%m}")
        self.assertEqual(old.context["total_mes"], Decimal("100.00"))

        detail = self.client.get(reverse("painel:funcionario", args=[self.ana.pk]))
        self.assertEqual([m["total"] for m in detail.context["por_mes"]], [Decimal("80.00"), Decimal("100.00")])

        couriers = self.client.get(reverse("painel:entregadores"))
        self.assertEqual({r["entregador"].name: r["vales"] for r in couriers.context["linhas"]}["João"], Decimal("13.00"))

    def test_invalid_advance_is_rejected(self):
        self.assertEqual(self.add_advance(self.ana, "0").status_code, 200)
        Employee.objects.filter(pk=self.ana.pk).update(is_active=False)
        self.assertEqual(self.add_advance(self.ana, "20").status_code, 200)
        self.assertFalse(SalaryAdvance.objects.exists())

    def test_delete_advance(self):
        self.add_advance(self.ana, "20")
        advance = SalaryAdvance.objects.get()
        self.client.post(reverse("painel:vale_excluir", args=[advance.pk]), {"next": "https://evil.example/"})
        self.assertFalse(SalaryAdvance.objects.exists())

    def test_register_staff_and_keep_history(self):
        res = self.client.post(reverse("painel:funcionarios"), {"acao": "funcionario", "name": "Bia", "role": "atendimento", "phone": ""})
        self.assertEqual(res.status_code, 302)
        bia = Employee.objects.get(name="Bia")
        self.assertEqual((bia.role, bia.tenant, bia.is_active), ("atendimento", self.tenant, True))

        self.add_advance(bia, "10")
        self.client.post(reverse("painel:funcionario_excluir", args=[bia.pk]))
        self.assertTrue(Employee.objects.filter(pk=bia.pk).exists())

    def test_other_establishments_data_is_not_reachable(self):
        from apps.tenants.models import Tenant as T
        other = T.objects.create(name="Outra", slug="outra")
        stranger = Employee.objects.create(tenant=other, name="Estranho")
        self.assertEqual(self.client.get(reverse("painel:funcionario", args=[stranger.pk])).status_code, 404)
        self.assertEqual(self.add_advance(stranger, "10").status_code, 200)
        self.assertFalse(SalaryAdvance.objects.exists())


class PromotionTests(PainelTestCase):
    def promo_post(self, **changes):
        post = {
            "title": "Terça da Pizza", "coupon_code": "terca10", "discount_type": "percentage",
            "discount_value": "10", "min_order_value": "0", "is_active": "on",
            "show_top_banner": "on", "banner_text": "10% em todas as pizzas", "weekdays_allowed": [],
        }
        post.update(changes)
        return self.client.post(reverse("painel:promocao_nova"), post)

    def test_banner_promotion_reaches_the_site_and_is_applied(self):
        self.assertEqual(self.promo_post().status_code, 302)
        promo = Promotion.objects.get()
        self.assertEqual(promo.coupon_code, "TERCA10")
        self.assertEqual(promo.tenant, self.tenant)

        data = APIClient().get("/api/v1/catalog/site-data/").json()
        self.assertEqual(data["promocao"]["cupom"], "TERCA10")
        self.assertEqual(data["promocao"]["descontoPercentual"], 10.0)

        order = self.create_order(cupom="TERCA10", modalidade="retirada")
        self.assertEqual(order.discount_amount, Decimal("7.69"))

    def test_banner_requires_rules_the_site_can_apply(self):
        res = self.promo_post(discount_type="fixed", min_order_value="50")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(Promotion.objects.exists())

    def test_paused_promotion_leaves_the_site(self):
        self.promo_post()
        promo = Promotion.objects.get()
        self.client.post(reverse("painel:promocao_ativa", args=[promo.pk]))
        data = APIClient().get("/api/v1/catalog/site-data/").json()
        self.assertFalse(data["promocao"]["ativa"])


class CustomersTests(PainelTestCase):
    def test_customers_grouped_by_whatsapp(self):
        self.create_order()
        self.create_order()
        res = self.client.get(reverse("painel:clientes"))
        self.assertContains(res, "Maria Silva")
        self.assertEqual(res.context["pagina"].object_list[0]["pedidos"], 2)

    def test_toggle_vip(self):
        user = User.objects.create_user(username="65911112222", password="senha-forte-123")
        profile = CustomerProfile.objects.create(user=user, tenant=self.tenant, whatsapp="65911112222")
        self.client.post(reverse("painel:cliente_vip", args=[profile.pk]))
        profile.refresh_from_db()
        self.assertTrue(profile.is_vip)


class SiteDataShapeTests(PainelTestCase):
    def test_site_data_matches_the_site_files(self):
        data = APIClient().get("/api/v1/catalog/site-data/").json()
        categories = {c["id"]: c for c in data["cardapio"]["categorias"]}
        self.assertNotIn("compre-junto", categories)
        pizza = next(i for i in categories["pizzas-salgadas"]["itens"] if i["id"] == "pizza-americana")
        self.assertEqual(pizza["categoriaPreco"], "premium")
        self.assertEqual(pizza["precos"], {"pequena": 61.9, "media": 72.9, "grande": 86.9})
        combo = next(i for i in categories["combos-pizzas"]["itens"] if i["id"] == "combo-duas-grandes")
        self.assertIsNone(combo["preco"])
        self.assertIn("composicao", combo)
        self.assertEqual(len(data["horario"]["dias"]), 7)
        self.assertIn({"id": "bebida-guarana-1-5l", "preco": 14.0, "disponivel": True}, data["compreJunto"])
