"""Seed a small demo dataset: plans, products, users, and a couple of
members -- useful for first-run exploration.

    python manage.py seed_demo
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.members.models import Member
from apps.memberships.models import MembershipPlan, PlanType
from apps.products.models import Product

User = get_user_model()


class Command(BaseCommand):
    help = "Seed demo plans, products, users and members."

    def handle(self, *args, **options):
        if not User.objects.filter(username="owner").exists():
            User.objects.create_superuser("owner", password="owner12345", role="OWNER")
            self.stdout.write(self.style.SUCCESS("Created superuser 'owner' / 'owner12345'"))

        if not User.objects.filter(username="reception").exists():
            u = User.objects.create_user("reception", password="reception12345", role="RECEPTIONIST")
            u.is_staff = True
            u.save()
            self.stdout.write(self.style.SUCCESS("Created receptionist 'reception' / 'reception12345'"))

        daily, _ = MembershipPlan.objects.get_or_create(
            plan_type=PlanType.DAILY, name="Kunlik",
            defaults={"price": Decimal("20000"), "duration_days": 1},
        )
        MembershipPlan.objects.get_or_create(
            plan_type=PlanType.MONTHLY, name="Oylik",
            defaults={"price": Decimal("300000"), "duration_days": 30},
        )

        products = [
            ("Protein", "PRT-001", "kg", 200000, 5),
            ("BCAA", "BCAA-001", "dona", 150000, 10),
            ("Creatine", "CRT-001", "dona", 120000, 8),
            ("Pre-workout", "PWO-001", "dona", 180000, 6),
            ("Shake", "SHK-001", "dona", 20000, 30),
            ("Suv", "WTR-001", "dona", 5000, 100),
        ]
        for name, sku, unit, price, stock in products:
            Product.objects.get_or_create(
                sku=sku, defaults={
                    "name": name, "unit": unit, "sale_price": Decimal(price),
                    "stock_quantity": Decimal(stock), "low_stock_threshold": Decimal(3),
                },
            )

        for i, (first, last, phone) in enumerate([
            ("Ali", "Valiyev", "+998901112233"),
            ("Sardor", "Karimov", "+998901112244"),
            ("Bekzod", "Yusupov", "+998901112255"),
        ], start=1):
            Member.objects.get_or_create(
                phone=phone, defaults={
                    "member_code": Member.generate_member_code(),
                    "first_name": first, "last_name": last,
                },
            )

        self.stdout.write(self.style.SUCCESS("Demo data seeded."))
