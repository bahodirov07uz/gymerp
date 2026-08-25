from decimal import Decimal

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class TransactionType(models.TextChoices):
    MEMBERSHIP_CHARGE = "MEMBERSHIP_CHARGE", "A'zolik to'lovi"
    DAILY_CHARGE = "DAILY_CHARGE", "Kunlik to'lov"
    PRODUCT_CHARGE = "PRODUCT_CHARGE", "Mahsulot sotuvi"
    MANUAL_CHARGE = "MANUAL_CHARGE", "Qo'lda qo'shilgan qarz"
    PAYMENT = "PAYMENT", "To'lov"
    ADJUSTMENT = "ADJUSTMENT", "Tuzatish"


class Direction(models.TextChoices):
    DEBIT = "DEBIT", "Qarz (+)"     # increases what the member owes
    CREDIT = "CREDIT", "To'lov (-)"  # decreases what the member owes


class LedgerTransaction(models.Model):
    """The single source of truth for a member's financial history.

    Every charge (membership, daily plan, product purchase, manual
    adjustment) and every payment is recorded here as an immutable
    entry. Balance is *always* derived from this table -- it is never
    cached on the Member model, because a cached field can silently
    drift out of sync with reality.
    """

    member = models.ForeignKey("members.Member", on_delete=models.PROTECT, related_name="ledger_entries")
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    direction = models.CharField(max_length=6, choices=Direction.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)

    # Generic reference to whatever created this entry (Membership,
    # ProductSale, Payment, ...) so the ledger stays fully traceable.
    reference_content_type = models.ForeignKey(
        ContentType, null=True, blank=True, on_delete=models.SET_NULL
    )
    reference_object_id = models.PositiveIntegerField(null=True, blank=True)
    reference = GenericForeignKey("reference_content_type", "reference_object_id")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # Reversal support -- financial rows are never deleted or edited.
    reversed_by = models.OneToOneField(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="reverses"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["member", "created_at"]),
            models.Index(fields=["transaction_type"]),
        ]

    def __str__(self):
        sign = "+" if self.direction == Direction.DEBIT else "-"
        return f"{self.member} {sign}{self.amount} ({self.get_transaction_type_display()})"

    @property
    def signed_amount(self) -> Decimal:
        return self.amount if self.direction == Direction.DEBIT else -self.amount

    def save(self, *args, **kwargs):
        # Ledger rows are append-only. Allow the initial insert; block edits.
        if self.pk is not None:
            raise ValueError(
                "LedgerTransaction rows are immutable. Create a reversal/adjustment "
                "entry instead of editing an existing one."
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("LedgerTransaction rows cannot be deleted. Use a reversal entry instead.")


class PaymentMethod(models.TextChoices):
    CASH = "CASH", "Naqd"
    CARD = "CARD", "Plastik karta"
    TRANSFER = "TRANSFER", "O'tkazma"
    OTHER = "OTHER", "Boshqa"


class Payment(models.Model):
    member = models.ForeignKey("members.Member", on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    payment_method = models.CharField(max_length=10, choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    reference = models.CharField(max_length=100, blank=True)
    note = models.CharField(max_length=255, blank=True)
    balance_before = models.DecimalField(max_digits=14, decimal_places=2)
    balance_after = models.DecimalField(max_digits=14, decimal_places=2)
    ledger_entry = models.OneToOneField(
        LedgerTransaction, null=True, blank=True, on_delete=models.SET_NULL, related_name="payment"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["member", "created_at"]),
        ]

    def __str__(self):
        return f"{self.member} to'lov {self.amount} ({self.created_at:%Y-%m-%d})"
