from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import Client, TestCase

from apps.billing.models import TransactionType
from apps.billing.services import post_charge
from apps.members.models import Member

User = get_user_model()


class ReceptionistCannotModifyFinancialDataTests(TestCase):
    """Receptionist must NOT be able to reverse/delete financial
    transactions, change product cost, or modify system settings."""

    def setUp(self):
        self.member = Member.objects.create(
            member_code="M-000001", first_name="Ali", last_name="Valiyev", phone="+998901112233",
        )
        self.entry = post_charge(
            member=self.member, transaction_type=TransactionType.MANUAL_CHARGE,
            amount=Decimal("10000"), description="test",
        )
        self.receptionist = User.objects.create_user("recep", password="pass12345", role="RECEPTIONIST")
        self.manager = User.objects.create_user("mgr", password="pass12345", role="MANAGER")

    def test_receptionist_cannot_reverse_ledger_entry_view(self):
        client = Client()
        client.login(username="recep", password="pass12345")
        response = client.post(f"/billing/ledger/{self.entry.pk}/reverse/", {"reason": "test"})
        self.assertEqual(response.status_code, 403)

    def test_manager_can_reverse_ledger_entry_view(self):
        client = Client()
        client.login(username="mgr", password="pass12345")
        response = client.post(f"/billing/ledger/{self.entry.pk}/reverse/", {"reason": "test"})
        self.assertEqual(response.status_code, 200)

    def test_receptionist_cannot_access_inventory_management(self):
        client = Client()
        client.login(username="recep", password="pass12345")
        response = client.get("/inventory/")
        self.assertEqual(response.status_code, 403)

    def test_ledger_transactions_are_never_deleted_only_reversed(self):
        # Financial records should preferably be immutable; correction
        # happens via a new reversal entry, not by deleting history.
        with self.assertRaises(ValueError):
            self.entry.delete()
