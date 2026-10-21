from unittest import mock
from django.test import override_settings
from django.urls import reverse
from apps.delivery.models import StoreSettings
from apps.integrations import evolution
from apps.painel.tests import PainelTestCase

QR = "data:image/png;base64,AAAA"
EVOLUTION = {"EVOLUTION_API_URL": "http://evolution.test", "EVOLUTION_API_KEY": "chave-teste"}


def fake_response(status, body):
    response = mock.Mock(status_code=status)
    response.json.return_value = body
    return response


@override_settings(**EVOLUTION)
class EvolutionClientTests(PainelTestCase):
    @mock.patch("apps.integrations.evolution.requests.request")
    def test_missing_instance_is_created_and_returns_the_qr(self, request):
        request.side_effect = [
            fake_response(404, {"response": {"message": ["The instance does not exist"]}}),
            fake_response(201, {"instance": {"instanceName": "don-corleone"}, "qrcode": {"base64": QR}}),
        ]
        self.assertEqual(evolution.connect_instance("don-corleone"), {"state": "connecting", "qr": QR})
        method, url = request.call_args_list[1].args
        self.assertEqual((method, url), ("POST", "http://evolution.test/instance/create"))
        self.assertEqual(request.call_args_list[1].kwargs["headers"], {"apikey": "chave-teste"})

    @mock.patch("apps.integrations.evolution.requests.request")
    def test_existing_instance_asks_for_a_new_qr(self, request):
        request.side_effect = [
            fake_response(200, {"instance": {"state": "close"}}),
            fake_response(200, {"base64": QR, "count": 1}),
        ]
        self.assertEqual(evolution.connect_instance("don-corleone")["qr"], QR)
        self.assertEqual(request.call_args_list[1].args[1], "http://evolution.test/instance/connect/don-corleone")

    @mock.patch("apps.integrations.evolution.requests.request", side_effect=evolution.requests.ConnectionError)
    def test_offline_api_raises_a_readable_error(self, request):
        with self.assertRaisesMessage(evolution.EvolutionError, "Não foi possível conectar à Evolution API"):
            evolution.connection_state("don-corleone")

    @mock.patch("apps.integrations.evolution.requests.request")
    def test_order_message_uses_the_store_instance_and_v2_payload(self, request):
        request.return_value = fake_response(201, {})
        StoreSettings.objects.filter(tenant=self.tenant).update(whatsapp_instance="minha-pizzaria")
        order = self.create_order()

        self.assertTrue(evolution.send_order_dispatched_notification(order))
        method, url = request.call_args.args
        self.assertEqual(url, "http://evolution.test/message/sendText/minha-pizzaria")
        payload = request.call_args.kwargs["json"]
        self.assertEqual(payload["number"], "5565999990000")
        self.assertIn(f"?rastreio={order.readable_code}", payload["text"])

    @mock.patch("apps.integrations.evolution.requests.request")
    def test_message_falls_back_to_the_documented_text_message_body(self, request):
        request.side_effect = [fake_response(400, {}), fake_response(201, {})]
        self.assertTrue(evolution.send_whatsapp_message("65999990000", "oi", "don-corleone"))
        self.assertEqual(request.call_args.kwargs["json"]["textMessage"], {"text": "oi"})

    @mock.patch("apps.integrations.evolution.requests.request")
    def test_both_error_formats_are_readable(self, request):
        for body in ({"error": {"code": "FORBIDDEN", "message": "Nome em uso"}},
                     {"response": {"message": ["Nome em uso"]}}):
            request.side_effect = [fake_response(404, {}), fake_response(403, body)]
            with self.assertRaisesMessage(evolution.EvolutionError, "Nome em uso"):
                evolution.connect_instance("don-corleone")

    @mock.patch("apps.integrations.evolution.requests.request")
    def test_profile_from_flat_or_wrapped_instance_list(self, request):
        flat = [{"name": "outra", "ownerJid": "5511@s.whatsapp.net"},
                {"name": "don-corleone", "ownerJid": "5565999990000@s.whatsapp.net", "profileName": "Don"}]
        wrapped = [{"instance": item} for item in flat]
        for body in (flat, wrapped):
            request.return_value = fake_response(200, body)
            self.assertEqual(evolution.instance_profile("don-corleone"), {"numero": "5565999990000", "nome": "Don"})

    @mock.patch("apps.integrations.evolution.requests.request", side_effect=evolution.requests.Timeout)
    def test_failed_message_does_not_raise(self, request):
        self.assertFalse(evolution.send_whatsapp_message("65999990000", "oi", "don-corleone"))


@override_settings(**EVOLUTION)
class WhatsappPageTests(PainelTestCase):
    @mock.patch("apps.integrations.evolution.connection_state", return_value="missing")
    def test_page_offers_to_create_the_instance(self, state):
        res = self.client.get(reverse("painel:whatsapp"))
        self.assertContains(res, "Criar e gerar QR Code")

    @mock.patch("apps.integrations.evolution.connection_state", return_value="close")
    @mock.patch("apps.integrations.evolution.connect_instance", return_value={"state": "connecting", "qr": QR})
    def test_connect_saves_the_instance_name_and_shows_the_qr(self, connect, state):
        res = self.client.post(reverse("painel:whatsapp_conectar"), {"instancia": "Don-Corleone"})
        self.assertContains(res, QR)
        connect.assert_called_once_with("don-corleone")
        self.assertEqual(StoreSettings.objects.get(tenant=self.tenant).whatsapp_instance, "don-corleone")

    def test_invalid_instance_name_is_rejected(self):
        res = self.client.post(reverse("painel:whatsapp_conectar"), {"instancia": "nome com espaço"})
        self.assertRedirects(res, reverse("painel:whatsapp"), fetch_redirect_response=False)
        self.assertEqual(StoreSettings.objects.get(tenant=self.tenant).whatsapp_instance, "")

    @mock.patch("apps.integrations.evolution.connection_state", side_effect=evolution.EvolutionError("API fora do ar"))
    def test_api_errors_are_shown_on_the_page(self, state):
        self.assertContains(self.client.get(reverse("painel:whatsapp")), "API fora do ar")

    @mock.patch("apps.integrations.evolution.connection_state", return_value="open")
    def test_status_endpoint_reports_the_connection(self, state):
        res = self.client.get(reverse("painel:whatsapp_estado"))
        self.assertEqual(res.json(), {"estado": "open"})

    @override_settings(EVOLUTION_API_KEY="")
    def test_page_explains_how_to_configure(self):
        self.assertContains(self.client.get(reverse("painel:whatsapp")), "docker compose up -d")

    def test_customers_cannot_open_the_page(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("painel:whatsapp")).status_code, 302)
