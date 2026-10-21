from django.urls import reverse
from rest_framework.test import APIClient
from apps.painel.tests import PainelTestCase


class OrderTrackingTests(PainelTestCase):
    def track(self, order):
        return APIClient().get(f"/api/v1/tracking/{order.readable_code}/").data

    def change(self, order, status, motivo=""):
        self.client.post(reverse("painel:pedido_status", args=[order.pk]), {"status": status, "motivo": motivo})

    def test_customer_sees_pending_then_in_preparation_then_sent(self):
        order = self.create_order()
        data = self.track(order)
        self.assertEqual(data["status_display"], "Pendente")
        self.assertEqual([s["label"] for s in data["timeline"]], ["Pendente", "Em preparo", "Enviado", "Entregue"])
        self.assertTrue(data["timeline"][0]["current"])
        self.assertIsNotNone(data["timeline"][0]["hora"])
        self.assertIsNone(data["previsao"])

        self.change(order, "PREPARO")
        data = self.track(order)
        self.assertEqual(data["status_display"], "Em preparo")
        self.assertTrue(data["timeline"][0]["completed"])
        self.assertTrue(data["timeline"][1]["current"])
        self.assertIsNotNone(data["timeline"][1]["hora"])
        self.assertTrue(data["previsao"].startswith("Chega entre"))

        self.change(order, "SAIU_PARA_ENTREGA")
        self.assertEqual(self.track(order)["status_display"], "Enviado")

        self.change(order, "CONCLUIDO")
        data = self.track(order)
        self.assertTrue(data["is_finalizado"])
        self.assertTrue(all(s["completed"] for s in data["timeline"]))

    def test_pickup_order_uses_pickup_steps(self):
        order = self.create_order(modalidade="retirada")
        labels = [s["label"] for s in self.track(order)["timeline"]]
        self.assertEqual(labels, ["Pendente", "Em preparo", "Pronto para retirada", "Retirado"])

    def test_cancelled_order_shows_the_reason(self):
        order = self.create_order()
        self.change(order, "CANCELADO", motivo="Pix não identificado")
        data = self.track(order)
        self.assertTrue(data["is_cancelado"])
        self.assertEqual(data["status_display"], "Cancelado")
        self.assertEqual(data["cancelamento"]["motivo"], "Pix não identificado")
        self.assertFalse(any(s["current"] for s in data["timeline"]))

    def test_unknown_code_returns_404(self):
        self.assertEqual(APIClient().get("/api/v1/tracking/DC-0000-ZZZ/").status_code, 404)
