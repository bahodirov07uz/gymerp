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
