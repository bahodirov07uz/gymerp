from decimal import Decimal

from django.db import transaction
from django.test import TestCase, TransactionTestCase

from apps.billing.models import PaymentMethod
from apps.billing.services import calculate_member_balance, create_payment, post_charge
from apps.billing.models import TransactionType
from apps.members.models import Member


class PaymentServiceTests(TestCase):
    def setUp(self):
        self.member = Member.objects.create(
            member_code="M-000001", first_name="Ali", last_name="Valiyev", phone="+998901112233",
        )
        post_charge(
            member=self.member, transaction_type=TransactionType.MEMBERSHIP_CHARGE,
            amount=Decimal("500000"), description="Oylik",
        )

    def test_payment_decreases_balance(self):
        create_payment(member=self.member, amount=Decimal("200000"), payment_method=PaymentMethod.CASH)
        self.assertEqual(calculate_member_balance(self.member), Decimal("300000.00"))

    def test_partial_payment_never_auto_clears_full_debt(self):
        payment = create_payment(member=self.member, amount=Decimal("200000"), payment_method=PaymentMethod.CASH)
        self.assertEqual(payment.balance_before, Decimal("500000.00"))
        self.assertEqual(payment.balance_after, Decimal("300000.00"))
        # remaining debt is still owed -- nothing marks it "paid in full"
        self.assertEqual(calculate_member_balance(self.member), Decimal("300000.00"))

    def test_multiple_partial_payments_add_up(self):
        create_payment(member=self.member, amount=Decimal("100000"), payment_method=PaymentMethod.CASH)
        create_payment(member=self.member, amount=Decimal("150000"), payment_method=PaymentMethod.CARD)
        self.assertEqual(calculate_member_balance(self.member), Decimal("250000.00"))

    def test_negative_or_zero_payment_rejected(self):
        with self.assertRaises(ValueError):
            create_payment(member=self.member, amount=Decimal("0"), payment_method=PaymentMethod.CASH)


class LedgerAtomicityTests(TransactionTestCase):
    """Verifies financial transactions are atomic: if any step in a
    multi-write operation fails, nothing is left half-committed."""

    def setUp(self):
        self.member = Member.objects.create(
            member_code="M-000001", first_name="Ali", last_name="Valiyev", phone="+998901112233",
        )

    def test_failed_sale_leaves_no_partial_ledger_or_stock_writes(self):
        from apps.products.models import Product
        from apps.sales.services import create_product_sale
        from apps.billing.models import LedgerTransaction

        plenty = Product.objects.create(name="Protein", sku="PRT-001", sale_price=Decimal("20000"),
                                         stock_quantity=Decimal("10"))
        scarce = Product.objects.create(name="BCAA", sku="BCAA-001", sale_price=Decimal("15000"),
                                         stock_quantity=Decimal("1"))

        with self.assertRaises(ValueError):
            create_product_sale(
                member=self.member,
                items=[
                    {"product": plenty, "quantity": 1},   # would succeed alone
                    {"product": scarce, "quantity": 100},  # fails -> whole sale rolls back
                ],
            )

        plenty.refresh_from_db()
        scarce.refresh_from_db()
        self.assertEqual(plenty.stock_quantity, Decimal("10"))  # untouched
        self.assertEqual(scarce.stock_quantity, Decimal("1"))   # untouched
        self.assertEqual(LedgerTransaction.objects.filter(member=self.member).count(), 0)

    def test_ledger_rows_are_immutable(self):
        entry = post_charge(
            member=self.member, transaction_type=TransactionType.MANUAL_CHARGE,
            amount=Decimal("1000"), description="test",
        )
        entry.amount = Decimal("999999")
        with self.assertRaises(ValueError):
            entry.save()
        with self.assertRaises(ValueError):
            entry.delete()
