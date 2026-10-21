import logging
import os
import subprocess
import sys
from io import StringIO
from pathlib import Path
from unittest import mock
from django.core.management import CommandError, call_command
from django.test import Client, SimpleTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.core.models import ErrorEvent
from apps.delivery.models import Employee
from apps.painel.tests import PainelTestCase

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent

CHECK_SCRIPT = (
    "import django; django.setup(); from django.conf import settings as s; "
    "print(s.DEBUG, s.CORS_ALLOW_ALL_ORIGINS, ','.join(s.ALLOWED_HOSTS))"
)


def load_production_settings(**env):
    """Loads config.settings.production in a fresh process with only the given variables."""
    clean_env = {k: v for k, v in os.environ.items() if k not in {
        "DJANGO_SECRET_KEY", "ALLOWED_HOSTS", "DATABASE_URL", "CORS_ALLOWED_ORIGINS"
    }}
    clean_env.update(env, DJANGO_SETTINGS_MODULE="config.settings.production")
    return subprocess.run(
        [sys.executable, "-c", CHECK_SCRIPT], cwd=BACKEND_DIR, env=clean_env, capture_output=True, text=True
    )


@override_settings(SUPPORT_WHATSAPP="")
class ErrorTrackingTests(PainelTestCase):
    """Unexpected errors: friendly page or JSON with an occurrence code, full context kept for support."""

    def setUp(self):
        super().setUp()
        logging.disable(logging.CRITICAL)  # the JSON log lines are expected here; keep the test output clean
        self.addCleanup(logging.disable, logging.NOTSET)

    def test_panel_error_shows_friendly_page_with_code(self):
        with mock.patch("apps.painel.views.common.store_status", side_effect=RuntimeError("falha no banco X")):
            res = self.client.get(reverse("painel:dashboard"))
        self.assertEqual(res.status_code, 500)
        event = ErrorEvent.objects.get()
        self.assertContains(res, event.code, status_code=500)
        self.assertContains(res, "Algo deu errado nesta tela", status_code=500)
        self.assertNotContains(res, "Traceback", status_code=500)
        self.assertNotContains(res, "falha no banco X", status_code=500)  # internal details stay internal
        self.assertRegex(event.code, r"^ERR-\d{4}-[2-9A-HJKMNP-Z]{4}$")
        self.assertEqual((event.area, event.user, event.exception_type), ("painel", self.staff, "builtins.RuntimeError"))
        self.assertIn("falha no banco X", event.traceback)
        self.assertRegex(event.origin, r"^apps[/\\]painel[/\\]views[/\\]common\.py:\d+ \(nav_context\)$")

    def test_api_error_returns_json_the_site_can_show(self):
        payload = {
            "cliente": {"nome": "Maria Silva", "telefone": "(65) 99999-0000"}, "senha": "segredo123",
            "modalidade": "retirada", "pagamento": {"forma": "pix"},
            "itens": [{"tipo": "pizza", "tamanho": {"id": "grande"}, "sabores": [{"id": "pizza-calabresa"}]}],
        }
        with mock.patch("apps.orders.views.CreateOrderSerializer.save", side_effect=ValueError("quebrou")):
            res = APIClient().post("/api/v1/orders/create/", payload, format="json")
        self.assertEqual(res.status_code, 500)
        event = ErrorEvent.objects.get()
        self.assertEqual(res.json()["codigoOcorrencia"], event.code)
        self.assertIn(event.code, res.json()["mensagem"])
        # What the customer sent is kept (DRF had already read the body), secrets are not
        body = event.request_data["body"]
        self.assertEqual(body["cliente"]["nome"], "Maria Silva")
        self.assertEqual(body["senha"], "[removido]")
        self.assertEqual((event.area, event.method), ("api", "POST"))

    def test_courier_app_error_uses_the_courier_message(self):
        courier = Employee.objects.create(tenant=self.tenant, name="Rafa", working_on=timezone.localdate())
        client = Client()
        client.get(reverse("entregador:entrar", args=[courier.new_access_token()]))
        with mock.patch("apps.painel.views.app_entregador.within_store_hours", side_effect=KeyError("x")):
            res = client.get(reverse("entregador:app"))
        self.assertContains(res, "Suas entregas continuam registradas", status_code=500)
        self.assertContains(res, ErrorEvent.objects.get().code, status_code=500)

    def test_not_found_and_forbidden_are_friendly_and_not_recorded(self):
        self.assertContains(self.client.get("/painel/nao-existe/"), "Página não encontrada", status_code=404)
        self.assertEqual(self.client.get("/api/v1/nao-existe/").json(), {"mensagem": "Endereço não encontrado."})
        customer = User.objects.create_user(username="65911112222", password="senha-forte-123")
        self.client.force_login(customer)
        self.assertContains(self.client.get(reverse("painel:dashboard")), "Acesso não permitido", status_code=403)
        self.assertFalse(ErrorEvent.objects.exists())

    @override_settings(SUPPORT_WHATSAPP="65988887777")
    def test_support_is_alerted_once_per_kind_of_error(self):
        with mock.patch("apps.core.errors.threading.Thread") as thread, \
                mock.patch("apps.painel.views.common.store_status", side_effect=RuntimeError("x")):
            self.client.get(reverse("painel:dashboard"))
            self.client.get(reverse("painel:dashboard"))
        self.assertEqual(thread.call_count, 1)  # second identical error within 30 min: no new alert
        self.assertEqual(ErrorEvent.objects.count(), 2)

    def test_support_command_shows_the_details(self):
        with mock.patch("apps.painel.views.common.store_status", side_effect=RuntimeError("detalhe interno")):
            self.client.get(reverse("painel:dashboard"))
        code = ErrorEvent.objects.get().code
        out = StringIO()
        call_command("ocorrencia", code.lower(), stdout=out)
        self.assertIn("RuntimeError: detalhe interno", out.getvalue())
        self.assertIn("Usuário:     dono", out.getvalue())
        with self.assertRaises(CommandError):
            call_command("ocorrencia", "ERR-0000-ZZZZ", stdout=StringIO())


class ProductionSettingsTests(SimpleTestCase):
    def test_production_refuses_to_start_without_secret_key(self):
        result = load_production_settings(ALLOWED_HOSTS="api.exemplo.com", DATABASE_URL="sqlite:///x.db")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DJANGO_SECRET_KEY", result.stderr)

    def test_production_refuses_wildcard_hosts(self):
        result = load_production_settings(DJANGO_SECRET_KEY="x" * 50, ALLOWED_HOSTS="*", DATABASE_URL="sqlite:///x.db")
        self.assertNotEqual(result.returncode, 0)

    def test_production_does_not_allow_every_origin(self):
        result = load_production_settings(
            DJANGO_SECRET_KEY="x" * 50, ALLOWED_HOSTS="api.exemplo.com", DATABASE_URL="sqlite:///x.db"
        )
        if "No module named 'dj_database_url'" in result.stderr or "No module named 'whitenoise'" in result.stderr:
            self.skipTest("Dependências de produção não instaladas (requirements/production.txt).")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.split(), ["False", "False", "api.exemplo.com"])
