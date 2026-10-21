"""
Production smoke test: panel login behind the proxy with CSRF enforced, as the real domain would see it.
Run inside the web container:
    python manage.py shell -c "exec(open('deploy/smoke_login.py', encoding='utf-8').read())"
"""
import re
from django.conf import settings
from django.test import Client
from apps.accounts.models import User

host = settings.ALLOWED_HOSTS[0]
proxy = {"HTTP_HOST": host, "HTTP_X_FORWARDED_PROTO": "https", "HTTP_ORIGIN": f"https://{host}"}
username = "smoke-test-login"
User.objects.filter(username=username).delete()
User.objects.create_user(username=username, password="SenhaDeTeste-123", is_staff=True)

client = Client(enforce_csrf_checks=True)
page = client.get("/painel/entrar/", **proxy)
token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', page.content.decode()).group(1)
login = client.post("/painel/entrar/", {"username": username, "password": "SenhaDeTeste-123",
                                         "csrfmiddlewaretoken": token}, **proxy)
dashboard = client.get("/painel/", **proxy)
print("login:", login.status_code, "->", login.headers.get("Location"))
print("painel depois do login:", dashboard.status_code)
print("cookie de sessão seguro (só HTTPS):", bool(client.cookies["sessionid"]["secure"]))
User.objects.filter(username=username).delete()
print("RESULTADO:", "OK" if login.status_code == 302 and dashboard.status_code == 200 else "FALHOU")
