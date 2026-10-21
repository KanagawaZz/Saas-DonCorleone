from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.orders.models import Order
from apps.tenants.models import Tenant


class ThermalReceiptTests(TestCase):
    def setUp(self):
        tenant = Tenant.objects.create(name="Don Corleone", slug="don-corleone")
        self.order = Order.objects.create(
            tenant=tenant,
            customer_name="<img src=x onerror=alert(1)>",
            customer_phone="65999990000",
            delivery_street="<script>alert(2)</script>",
            subtotal=Decimal("50.00"),
            total_amount=Decimal("50.00"),
        )
        self.url = f"/api/v1/printing/{self.order.readable_code}/"
        self.client = APIClient()

    def test_receipt_requires_staff_login(self):
        self.assertIn(self.client.get(self.url).status_code, (401, 403))

        customer = User.objects.create_user(username="cliente", password="x-segura-123")
        self.client.force_authenticate(customer)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_customer_text_is_escaped(self):
        staff = User.objects.create_user(username="cozinha", password="x-segura-123", is_staff=True)
        self.client.force_authenticate(staff)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertNotIn(b"<img src=x", res.content)
        self.assertNotIn(b"<script>alert(2)", res.content)
        self.assertIn(b"&lt;img src=x onerror=alert(1)&gt;", res.content)
