from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.attendance.models import Attendance
from apps.billing.models import PaymentMethod
from apps.billing.services import calculate_member_balance, debtors_queryset
from apps.members.models import Member
from apps.memberships.models import MembershipPlan, PlanType
from apps.memberships.services import create_membership, create_daily_membership
from apps.products.models import Product


class FullGymIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.manager = User.objects.create_user(
            username="manager1", password="password123", role=Role.MANAGER,
        )
        self.receptionist = User.objects.create_user(
            username="reception1", password="password123", role=Role.RECEPTIONIST,
        )
        self.member = Member.objects.create(
            member_code="M-000001",
            first_name="Jasur",
            last_name="Toshmatov",
            phone="+998901234567",
        )
        self.monthly_plan = MembershipPlan.objects.create(
            name="Oylik Standart",
            plan_type=PlanType.MONTHLY,
            price=Decimal("400000.00"),
            duration_days=30,
        )
        self.daily_plan = MembershipPlan.objects.create(
            name="Kunlik Reja",
            plan_type=PlanType.DAILY,
            price=Decimal("30000.00"),
            duration_days=1,
        )
        self.product = Product.objects.create(
            name="BCAA Drink",
            sku="BCAA-001",
            unit="dona",
            sale_price=Decimal("25000.00"),
            cost_price=Decimal("18000.00"),
            stock_quantity=Decimal("50"),
            low_stock_threshold=Decimal("10"),
        )

    def test_all_pages_return_200_for_authenticated_users(self):
        self.client.login(username="manager1", password="password123")
        urls = [
            reverse("dashboard:index"),
            reverse("dashboard:index") + "?date=invalid-date",  # tests bad date resilience
            reverse("members:reception"),
            reverse("members:list"),
            reverse("members:create"),
            reverse("members:profile", args=[self.member.pk]),
            reverse("billing:debtors"),
            reverse("billing:debtors") + "?q=Jasur",
            reverse("inventory:list"),
            reverse("reports:daily"),
            reverse("reports:daily") + "?date=bad-date",  # tests bad date resilience
            reverse("reports:monthly"),
            reverse("reports:monthly") + "?month=bad-month",  # tests bad month resilience
            reverse("reports:products"),
            reverse("reports:expiring"),
            reverse("reports:analytics"),
            reverse("reports:analytics") + "?days=7",
            reverse("reports:analytics") + "?days=90",
        ]
        for url in urls:
            with self.subTest(url=url):
                resp = self.client.get(url)
                self.assertEqual(resp.status_code, 200, f"Failed at URL: {url}")

    def test_full_reception_flow_end_to_end(self):
        self.client.login(username="reception1", password="password123")

        # 1. Search member via HTMX
        resp = self.client.get(reverse("members:list"), {"q": "Jasur"}, HTTP_HX_REQUEST="true")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Jasur Toshmatov")

        # 2. Add Daily Plan & Check-In (Check that OOB in-gym is returned)
        resp = self.client.post(reverse("attendance:add_daily_plan", args=[self.member.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'hx-swap-oob="true"')
        self.assertEqual(calculate_member_balance(self.member), Decimal("30000.00"))
        self.assertTrue(Attendance.objects.filter(member=self.member, check_out__isnull=True).exists())

        # 3. Add Product Sale (Multi-product selection)
        product2 = Product.objects.create(
            name="Protein Bar",
            sku="BAR-001",
            unit="dona",
            sale_price=Decimal("15000.00"),
            cost_price=Decimal("10000.00"),
            stock_quantity=Decimal("30"),
            low_stock_threshold=Decimal("5"),
        )
        resp = self.client.post(reverse("sales:add_product", args=[self.member.pk]), {
            "selected_products": [str(self.product.pk), str(product2.pk)],
            f"quantity_{self.product.pk}": "2",
            f"quantity_{product2.pk}": "3",
        })
        self.assertEqual(resp.status_code, 200)
        # Total debt: 30000 (daily) + 50000 (2 x 25000) + 45000 (3 x 15000) = 125000
        self.assertEqual(calculate_member_balance(self.member), Decimal("125000.00"))
        self.product.refresh_from_db()
        product2.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, Decimal("48"))
        self.assertEqual(product2.stock_quantity, Decimal("27"))

        # 4. Receive Payment (String amount tested)
        resp = self.client.post(reverse("billing:receive_payment", args=[self.member.pk]), {
            "amount": "125000",
            "payment_method": PaymentMethod.CASH,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(calculate_member_balance(self.member), Decimal("0.00"))

        # 5. Check-Out (Check OOB in-gym returned)
        resp = self.client.post(reverse("attendance:check_out", args=[self.member.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'hx-swap-oob="true"')
        att = Attendance.objects.get(member=self.member)
        self.assertIsNotNone(att.check_out)

        # 6. Check-In AGAIN on the same day (should succeed because previous was checked out)
        create_membership(member=self.member, plan=self.monthly_plan)
        resp = self.client.post(reverse("attendance:check_in", args=[self.member.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Attendance.objects.filter(member=self.member).count(), 2)

    def test_debtors_queryset_accuracy(self):
        # Create debt for member
        create_daily_membership(member=self.member, plan=self.daily_plan)
        debtors = list(debtors_queryset())
        self.assertEqual(len(debtors), 1)
        self.assertEqual(debtors[0].annotated_balance, Decimal("30000.00"))
        self.assertEqual(debtors[0].pk, self.member.pk)

    def test_restock_view_with_decimal(self):
        self.client.login(username="manager1", password="password123")
        resp = self.client.post(reverse("inventory:restock", args=[self.product.pk]), {
            "quantity": "25",
            "note": "Yangi partiya",
        })
        self.assertEqual(resp.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, Decimal("75"))


class MemberProfileActionsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.manager = User.objects.create_user(
            username="manager2", password="password123", role=Role.MANAGER,
        )
        self.receptionist = User.objects.create_user(
            username="reception2", password="password123", role=Role.RECEPTIONIST,
        )
        self.member = Member.objects.create(
            member_code="M-000009",
            first_name="Anvar",
            last_name="Saidov",
            phone="+998939998877",
        )
        self.monthly_plan = MembershipPlan.objects.create(
            name="Oylik Standart",
            plan_type=PlanType.MONTHLY,
            price=Decimal("400000.00"),
            duration_days=30,
        )

    def test_add_membership_from_profile_increases_balance(self):
        self.client.login(username="reception2", password="password123")
        resp = self.client.post(
            reverse("members:add_membership", args=[self.member.pk]),
            {"plan_id": self.monthly_plan.pk, "start_date": ""},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(calculate_member_balance(self.member), Decimal("400000.00"))
        self.assertEqual(self.member.memberships.count(), 1)
        self.assertContains(resp, "Oylik Standart")

    def test_add_payment_from_profile_decreases_balance(self):
        # 1. Create initial membership debt
        create_membership(member=self.member, plan=self.monthly_plan)
        self.assertEqual(calculate_member_balance(self.member), Decimal("400000.00"))

        # 2. Add payment from profile
        self.client.login(username="reception2", password="password123")
        resp = self.client.post(
            reverse("members:add_payment", args=[self.member.pk]),
            {"amount": "150000", "payment_method": "CASH", "note": "Kassaga to'lov"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(calculate_member_balance(self.member), Decimal("250000.00"))
        self.assertEqual(self.member.payments.count(), 1)

    def test_add_manual_charge_by_manager_succeeds(self):
        self.client.login(username="manager2", password="password123")
        resp = self.client.post(
            reverse("members:add_manual_charge", args=[self.member.pk]),
            {"amount": "50000", "description": "Shkaf ijarasi"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(calculate_member_balance(self.member), Decimal("50000.00"))
        self.assertContains(resp, "Shkaf ijarasi")

    def test_add_manual_charge_by_receptionist_forbidden(self):
        self.client.login(username="reception2", password="password123")
        resp = self.client.post(
            reverse("members:add_manual_charge", args=[self.member.pk]),
            {"amount": "50000", "description": "Ruxsatsiz urinish"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(calculate_member_balance(self.member), Decimal("0.00"))


