from decimal import Decimal

from django.test import TestCase

from apps.billing.services import calculate_member_balance
from apps.members.models import Member
from apps.products.models import Product
from apps.sales.models import ProductSale
from apps.sales.services import create_product_sale


class ProductSaleServiceTests(TestCase):
    def setUp(self):
        self.member = Member.objects.create(
            member_code="M-000001", first_name="Ali", last_name="Valiyev", phone="+998901112233",
        )
        self.protein = Product.objects.create(
            name="Protein", sku="PRT-001", sale_price=Decimal("20000"), stock_quantity=Decimal("10"),
        )
        self.bcaa = Product.objects.create(
            name="BCAA", sku="BCAA-001", sale_price=Decimal("15000"), stock_quantity=Decimal("5"),
        )

    def test_product_sale_creates_charge(self):
        create_product_sale(member=self.member, items=[{"product": self.protein, "quantity": 1}])
        self.assertEqual(calculate_member_balance(self.member), Decimal("20000.00"))

    def test_product_sale_decreases_stock(self):
        create_product_sale(member=self.member, items=[{"product": self.protein, "quantity": 2}])
        self.protein.refresh_from_db()
        self.assertEqual(self.protein.stock_quantity, Decimal("8"))

    def test_insufficient_stock_prevents_sale(self):
        with self.assertRaises(ValueError):
            create_product_sale(member=self.member, items=[{"product": self.bcaa, "quantity": 999}])
        self.bcaa.refresh_from_db()
        # stock untouched and no charge posted -- the whole sale rolled back
        self.assertEqual(self.bcaa.stock_quantity, Decimal("5"))
        self.assertEqual(calculate_member_balance(self.member), Decimal("0.00"))
        self.assertEqual(ProductSale.objects.filter(member=self.member).count(), 0)

    def test_multiple_products_calculate_correctly(self):
        sale = create_product_sale(
            member=self.member,
            items=[
                {"product": self.protein, "quantity": 1},
                {"product": self.bcaa, "quantity": 1},
            ],
        )
        self.assertEqual(sale.total_amount, Decimal("35000.00"))
        self.assertEqual(calculate_member_balance(self.member), Decimal("35000.00"))
        self.protein.refresh_from_db()
        self.bcaa.refresh_from_db()
        self.assertEqual(self.protein.stock_quantity, Decimal("9"))
        self.assertEqual(self.bcaa.stock_quantity, Decimal("4"))


class ProductSearchViewTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(username="cashier", password="password")
        self.client.force_login(self.user)

        self.member = Member.objects.create(
            member_code="M-000002", first_name="Zafar", last_name="Aliyev", phone="+998901234567",
        )

        # Create 55 products: 30 Protein variants, 25 Water variants
        products = []
        for i in range(1, 31):
            products.append(Product(
                name=f"Protein Shake #{i}",
                sku=f"PRT-SHK-{i:03d}",
                sale_price=Decimal("25000"),
                stock_quantity=Decimal("50"),
                is_active=True,
            ))
        for i in range(1, 26):
            products.append(Product(
                name=f"Mineral Suv #{i}",
                sku=f"WTR-MIN-{i:03d}",
                sale_price=Decimal("5000"),
                stock_quantity=Decimal("100"),
                is_active=True,
            ))
        Product.objects.bulk_create(products)

    def test_empty_query_returns_empty_results(self):
        response = self.client.get("/sales/products/search/?q=")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["products"]), 0)
        self.assertContains(response, "Mahsulot nomini yozing...")

    def test_short_query_returns_empty_results(self):
        response = self.client.get("/sales/products/search/?q=p")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["products"]), 0)
        self.assertTrue(response.context.get("too_short"))
        self.assertContains(response, "Yana harf yozing...")

    def test_query_returns_at_most_15_matches(self):
        response = self.client.get("/sales/products/search/?q=prot")
        self.assertEqual(response.status_code, 200)
        matches = response.context["products"]
        self.assertEqual(len(matches), 15)
        for prod in matches:
            self.assertIn("protein", prod.name.lower())

    def test_multi_product_sale_submission(self):
        p1 = Product.objects.filter(name__icontains="Protein").first()
        p2 = Product.objects.filter(name__icontains="Suv").first()

        post_data = {
            "selected_products": [p1.pk, p2.pk],
            f"quantity_{p1.pk}": "2",
            f"quantity_{p2.pk}": "3",
        }

        response = self.client.post(f"/sales/{self.member.pk}/add-product/", post_data)
        self.assertEqual(response.status_code, 200)

        # Total expected: 2 * 25000 + 3 * 5000 = 50000 + 15000 = 65000
        balance = calculate_member_balance(self.member)
        self.assertEqual(balance, Decimal("65000.00"))

        p1.refresh_from_db()
        p2.refresh_from_db()
        self.assertEqual(p1.stock_quantity, Decimal("48"))
        self.assertEqual(p2.stock_quantity, Decimal("97"))
