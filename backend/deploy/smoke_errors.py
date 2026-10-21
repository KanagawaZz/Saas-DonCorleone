"""
Production smoke test for the error pages: forces an unexpected error in the panel and checks that
the user gets the friendly page with an occurrence code and that the occurrence was recorded.
Run inside the web container:
    python manage.py shell -c "exec(open('deploy/smoke_errors.py', encoding='utf-8').read())"
"""
from unittest import mock
from django.conf import settings
from django.test import Client
from apps.accounts.models import User
from apps.core.models import ErrorEvent

host = settings.ALLOWED_HOSTS[0]
proxy = {"HTTP_HOST": host, "HTTP_X_FORWARDED_PROTO": "https"}
username = "smoke-test-errors"
User.objects.filter(username=username).delete()
user = User.objects.create_user(username=username, password="x", is_staff=True)
client = Client(raise_request_exception=False)
client.force_login(user)

with mock.patch("apps.painel.views.common.store_status", side_effect=RuntimeError("teste de ocorrência")):
    page = client.get("/painel/", **proxy)
event = ErrorEvent.objects.filter(message="teste de ocorrência").first()
html = page.content.decode()
checks = {
    "status 500": page.status_code == 500,
    "tela amigável": "Algo deu errado nesta tela" in html,
    "sem traceback na tela": "Traceback" not in html and "teste de ocorrência" not in html,
    "ocorrência gravada": event is not None,
    "código na tela": bool(event) and event.code in html,
    "origem no nosso código": bool(event) and "common.py" in event.origin,
}
not_found = client.get("/painel/nao-existe/", **proxy)
checks["404 amigável"] = not_found.status_code == 404 and "Página não encontrada" in not_found.content.decode()
api = client.get("/api/v1/nao-existe/", **proxy)
checks["404 da API em JSON"] = api.status_code == 404 and api.json().get("mensagem") == "Endereço não encontrado."

for name, ok in checks.items():
    print(f"[{'OK ' if ok else 'FALHOU'}] {name}")
print("código:", event.code if event else "-")
if event:
    event.delete()
User.objects.filter(username=username).delete()
print("RESULTADO:", "OK" if all(checks.values()) else "FALHOU")
