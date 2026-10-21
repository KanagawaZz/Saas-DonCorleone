from decimal import Decimal
from io import StringIO
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.catalog.models import Product
from apps.delivery.models import OperatingHour, StoreSettings
from apps.orders.models import Order
from apps.promotions.models import Promotion
from apps.tenants.models import Tenant

CREATE_URL = "/api/v1/orders/create/"


def pizza(sabores, tamanho="grande", borda=None, **extra):
    return {
        "tipo": "pizza",
        "quantidade": 1,
        "tamanho": {"id": tamanho},
        "borda": {"id": borda} if borda else None,
        "sabores": [{"id": s} for s in sabores],
        **extra,
    }


class CreateOrderPricingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("import_legacy_data", stdout=StringIO())
        # Always open, so these tests do not depend on the time they run
        OperatingHour.objects.update(opening_time="00:00", closing_time="23:59", is_active=True)

    def setUp(self):
        cache.clear()  # request throttling counters
        self.client = APIClient()

    def order(self, itens, **overrides):
        body = {
            "cliente": {"nome": "Cliente Teste", "telefone": "(65) 99999-0000"},
            "modalidade": "retirada",
            "pagamento": {"forma": "pix"},
            "itens": itens,
            **overrides,
        }
        return self.client.post(CREATE_URL, body, format="json")

    def test_pizza_with_paid_crust_is_priced_by_the_server(self):
        # precoUnitario is what the site's JS sends (76.9 + 9.9); it must be ignored, not rejected
        res = self.order([pizza(["pizza-calabresa"], borda="borda-cheddar", precoUnitario=76.9 + 9.9)])
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(Decimal(str(res.data["total"])), Decimal("86.80"))

    def test_highest_flavor_price_rule(self):
        res = self.order([pizza(["pizza-calabresa", "pizza-americana"])])
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(Decimal(str(res.data["total"])), Decimal("86.90"))
        flavors = Order.objects.get(readable_code=res.data["codigoPedido"]).items.get().flavors.all()
        self.assertEqual({f.proportion for f in flavors}, {"1/2"})

    def test_price_from_catalog_changes_follow_the_database(self):
        Product.objects.get(slug="pizza-calabresa").size_prices.filter(size_id="grande").update(price=Decimal("80.00"))
        res = self.order([pizza(["pizza-calabresa"])])
        self.assertEqual(Decimal(str(res.data["total"])), Decimal("80.00"))

    def test_client_price_is_ignored_for_simple_items(self):
        res = self.order([{"tipo": "simples", "idProduto": "kit-esfiha-3", "quantidade": 1, "precoUnitario": 0.01}])
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(Decimal(str(res.data["total"])), Decimal("57.90"))

    def test_unknown_product_is_rejected(self):
        res = self.order([{"tipo": "simples", "idProduto": "nao-existe", "quantidade": 1, "precoUnitario": 0.01}])
        self.assertEqual(res.status_code, 400)

    def test_unknown_flavor_is_rejected(self):
        res = self.order([pizza(["sabor-inventado"])])
        self.assertEqual(res.status_code, 400)

    def test_simple_product_cannot_be_used_as_pizza_flavor(self):
        res = self.order([pizza(["esfiha-carne"])])
        self.assertEqual(res.status_code, 400)

    def test_too_many_flavors_is_rejected(self):
        res = self.order([pizza(["pizza-calabresa", "pizza-mussarela", "pizza-milho"], tamanho="media")])
        self.assertEqual(res.status_code, 400)
        res = self.order([pizza(["pizza-calabresa", "pizza-mussarela", "pizza-milho"], tamanho="grande")])
        self.assertEqual(res.status_code, 201, res.data)

    def test_unknown_size_and_crust_are_rejected(self):
        self.assertEqual(self.order([pizza(["pizza-calabresa"], tamanho="gigante")]).status_code, 400)
        self.assertEqual(self.order([pizza(["pizza-calabresa"], borda="borda-ouro")]).status_code, 400)

    def test_sold_out_product_is_rejected(self):
        Product.objects.filter(slug="pizza-calabresa").update(is_available=False)
        self.assertEqual(self.order([pizza(["pizza-calabresa"])]).status_code, 400)

    def test_minimum_order(self):
        res = self.order([{"tipo": "simples", "idProduto": "esfiha-carne", "quantidade": 1}])
        self.assertEqual(res.status_code, 400)
        res = self.order([{"tipo": "simples", "idProduto": "esfiha-carne", "quantidade": 4}])
        self.assertEqual(res.status_code, 201, res.data)

    def test_compre_junto_items_are_priced(self):
        res = self.order([pizza(["pizza-calabresa"]), {"tipo": "simples", "idProduto": "bebida-guarana-1-5l", "quantidade": 1, "precoUnitario": 1}])
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(Decimal(str(res.data["total"])), Decimal("90.90"))

    def test_price_on_request_item_is_flagged_for_the_attendant(self):
        res = self.order([pizza(["pizza-calabresa"]), {"tipo": "simples", "idProduto": "combo-duas-grandes", "quantidade": 1}])
        self.assertEqual(res.status_code, 201, res.data)
        item = Order.objects.get(readable_code=res.data["codigoPedido"]).items.get(product__slug="combo-duas-grandes")
        self.assertEqual(item.unit_price_snapshot, Decimal("0.00"))
        self.assertIn("sob consulta", item.notes.lower())

    def test_delivery_fee_from_zone_and_pending_for_unknown_neighborhood(self):
        res = self.order([pizza(["pizza-calabresa"])], modalidade="entrega", endereco={"bairro": "Cidade Alta"})
        self.assertEqual(Decimal(res.data["detalhes"]["delivery_fee"]), Decimal("5.00"))

        res = self.order([pizza(["pizza-calabresa"])], modalidade="entrega", endereco={"bairro": "Bairro Longe"})
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(Decimal(res.data["detalhes"]["delivery_fee"]), Decimal("0.00"))
        self.assertIn("TAXA DE ENTREGA A CONFIRMAR", res.data["detalhes"]["notes"])

    def test_closed_store_rejects_orders(self):
        OperatingHour.objects.update(is_active=False)
        self.assertEqual(self.order([pizza(["pizza-calabresa"])]).status_code, 400)

    def test_emergency_closed_rejects_orders(self):
        StoreSettings.objects.update(emergency_closed=True, emergency_closed_reason="Fechado por chuva")
        res = self.order([pizza(["pizza-calabresa"])])
        self.assertEqual(res.status_code, 400)

    def test_coupon_discount_and_usage_limit(self):
        Promotion.objects.create(
            tenant=Tenant.objects.get(), title="Dez", coupon_code="DEZ", discount_value=Decimal("10"), max_uses=1
        )
        res = self.order([pizza(["pizza-calabresa"])], cupom="dez")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(Decimal(str(res.data["total"])), Decimal("69.21"))

        # Limit reached: the order is still saved, without discount and with a note for the attendant
        res = self.order([pizza(["pizza-calabresa"])], cupom="DEZ")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(Decimal(str(res.data["total"])), Decimal("76.90"))
        self.assertIn("CUPOM DEZ NÃO APLICADO", res.data["detalhes"]["notes"])
        self.assertEqual(Promotion.objects.get(coupon_code="DEZ").current_uses, 1)

    def test_vip_coupon_requires_login(self):
        Promotion.objects.create(
            tenant=Tenant.objects.get(), title="VIP", coupon_code="VIP", discount_value=Decimal("10"),
            registered_customers_only=True,
        )
        res = self.order([pizza(["pizza-calabresa"])], cupom="VIP")
        self.assertEqual(Decimal(str(res.data["total"])), Decimal("76.90"))

        customer = User.objects.create_user(username="65988887777", password="senha-forte-123")
        self.client.force_authenticate(customer)
        res = self.order([pizza(["pizza-calabresa"])], cupom="VIP")
        self.assertEqual(Decimal(str(res.data["total"])), Decimal("69.21"))
        self.assertEqual(Order.objects.get(readable_code=res.data["codigoPedido"]).customer_user, customer)

    def test_full_address_from_the_site_payload_is_saved(self):
        res = self.order(
            [pizza(["pizza-calabresa"])],
            modalidade="entrega",
            endereco={"logradouro": "Rua das Flores", "numero": "10", "complemento": "Apto 3",
                      "bairro": "Cidade Alta", "referencia": "Perto da praça", "cep": "78000-000"},
            pagamento={"forma": "dinheiro", "precisaTroco": "sim", "trocoPara": "R$ 1.000,00"},
        )
        self.assertEqual(res.status_code, 201, res.data)
        order = Order.objects.get(readable_code=res.data["codigoPedido"])
        self.assertEqual(order.delivery_street, "Rua das Flores")
        self.assertEqual(order.delivery_complement, "Apto 3")
        self.assertEqual(order.delivery_zipcode, "78000-000")
        self.assertEqual(order.change_for, Decimal("1000.00"))
        self.assertEqual(order.calculated_change, Decimal("1000.00") - order.total_amount)

    def test_invalid_payment_method_is_rejected(self):
        res = self.order([pizza(["pizza-calabresa"])], pagamento={"forma": "bitcoin"})
        self.assertEqual(res.status_code, 400)

    def test_same_idempotency_key_returns_the_same_order(self):
        first = self.order([pizza(["pizza-calabresa"])], idempotencyKey="chave-1")
        second = self.order([pizza(["pizza-calabresa"])], idempotencyKey="chave-1")
        self.assertEqual(first.data["codigoPedido"], second.data["codigoPedido"])
        self.assertEqual(Order.objects.count(), 1)
