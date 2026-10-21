from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.tenants.models import Tenant


class CustomerAuthTests(TestCase):
    def setUp(self):
        cache.clear()  # request throttling counters
        Tenant.objects.create(name="Don Corleone", slug="don-corleone")
        self.client = APIClient()

    def register(self, **overrides):
        # Same payload the site's Clube VIP modal sends (no username)
        body = {"name": "Ana Souza", "whatsapp": "(65) 98888-7777", "neighborhood": "Centro", "password": "pizza-boa-2026"}
        body.update(overrides)
        return self.client.post("/api/v1/accounts/register/", body, format="json")

    def test_register_with_site_payload_uses_whatsapp_as_login(self):
        res = self.register()
        self.assertEqual(res.status_code, 201, res.data)
        self.assertIn("token", res.data)
        user = User.objects.get()
        self.assertEqual(user.username, "65988887777")
        self.assertEqual(user.customer_profile.default_address_neighborhood, "Centro")

    def test_duplicate_whatsapp_is_rejected(self):
        self.register()
        res = self.register(whatsapp="65988887777")
        self.assertEqual(res.status_code, 400)
        self.assertIn("whatsapp", res.data)

    def test_weak_password_is_rejected(self):
        self.assertEqual(self.register(password="123456").status_code, 400)

    def test_login_accepts_formatted_whatsapp(self):
        self.register()
        res = self.client.post("/api/v1/accounts/login/", {"username": "(65) 98888-7777", "password": "pizza-boa-2026"}, format="json")
        self.assertEqual(res.status_code, 200, res.data)

    def test_customer_admin_routes_are_registered_and_staff_only(self):
        url = "/api/v1/customers/admin/customers/"
        self.assertIn(self.client.get(url).status_code, (401, 403))
        staff = User.objects.create_user(username="dono", password="senha-forte-123", is_staff=True)
        self.client.force_authenticate(staff)
        self.assertEqual(self.client.get(url).status_code, 200)
