"""Billing service layer.

Business rule: the ledger is the ONLY source of truth for a member's
balance. Nothing else may be trusted for financial totals, and this
module is the single place that is allowed to write to
``LedgerTransaction``.
"""
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum, Case, When, F, DecimalField, Value
from django.db.models.functions import Coalesce

from apps.audit.services import log_action

from .models import Direction, LedgerTransaction, Payment, TransactionType


def post_charge(*, member, transaction_type, amount, description="", reference=None, created_by=None):
    """Record a DEBIT (charge) entry. Used by memberships/sales/manual charges."""
    if amount <= 0:
        raise ValueError("Charge amount must be positive.")
    entry = LedgerTransaction.objects.create(
        member=member,
        transaction_type=transaction_type,
        direction=Direction.DEBIT,
        amount=amount,
        description=description,
        reference=reference,
        created_by=created_by,
    )
    log_action(user=created_by, action="ledger_charge", obj=entry, metadata={
        "member_id": member.pk, "amount": str(amount), "type": transaction_type,
    })
    return entry


def calculate_member_balance(member) -> Decimal:
    """Outstanding balance = total_charges - total_payments, computed
    directly from the ledger (never from a cached field)."""
    agg = LedgerTransaction.objects.filter(member=member).aggregate(
        total=Coalesce(
            Sum(
                Case(
                    When(direction=Direction.DEBIT, then=F("amount")),
                    When(direction=Direction.CREDIT, then=-F("amount")),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            ),
            Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2)),
        )
    )
    return agg["total"]


@transaction.atomic
def create_payment(*, member, amount, payment_method, reference="", note="", created_by=None):
    """Record a partial or full payment. The system never auto-marks a
    debt as fully paid -- it only records exactly what was received."""
    if amount <= 0:
        raise ValueError("Payment amount must be positive.")

    balance_before = calculate_member_balance(member)

    ledger_entry = LedgerTransaction.objects.create(
        member=member,
        transaction_type=TransactionType.PAYMENT,
        direction=Direction.CREDIT,
        amount=amount,
        description=note or "To'lov",
        created_by=created_by,
    )

    payment = Payment.objects.create(
        member=member,
        amount=amount,
        payment_method=payment_method,
        reference=reference,
        note=note,
        balance_before=balance_before,
        balance_after=balance_before - amount,
        ledger_entry=ledger_entry,
        created_by=created_by,
    )
    # link the ledger row's generic reference back to the payment
    ledger_entry.reference = payment
    LedgerTransaction.objects.filter(pk=ledger_entry.pk).update(
        reference_content_type=ledger_entry.reference_content_type_id
        if ledger_entry.reference_content_type_id
        else _content_type_id(payment),
        reference_object_id=payment.pk,
    )

    log_action(user=created_by, action="payment_created", obj=payment, metadata={
        "member_id": member.pk, "amount": str(amount), "balance_after": str(payment.balance_after),
    })
    return payment


def _content_type_id(obj):
    from django.contrib.contenttypes.models import ContentType
    return ContentType.objects.get_for_model(obj).pk


@transaction.atomic
def reverse_transaction(*, ledger_entry, reason, created_by):
    """Create an offsetting entry instead of deleting/editing history.
    Only OWNER/MANAGER roles may call this (enforced at the view layer)."""
    if ledger_entry.reversed_by_id:
        raise ValueError("This transaction has already been reversed.")

    opposite_direction = Direction.CREDIT if ledger_entry.direction == Direction.DEBIT else Direction.DEBIT
    reversal = LedgerTransaction.objects.create(
        member=ledger_entry.member,
        transaction_type=TransactionType.ADJUSTMENT,
        direction=opposite_direction,
        amount=ledger_entry.amount,
        description=f"Reversal: {reason}",
        created_by=created_by,
    )
    ledger_entry.reversed_by = reversal
    # reversed_by is the only field we ever touch on an existing ledger row,
    # and only via update() -- save() is intentionally blocked above.
    LedgerTransaction.objects.filter(pk=ledger_entry.pk).update(reversed_by=reversal)

    log_action(user=created_by, action="financial_adjustment", obj=reversal, metadata={
        "original_entry_id": ledger_entry.pk, "reason": reason,
    })
    return reversal


def debtors_queryset(search: str = ""):
    """Return an annotated queryset of active members who have a positive
    balance (charges > payments), sorted by balance descending.

    Uses a single SQL pass with conditional SUM -- no Python loop, no N+1.
    Each row exposes `annotated_balance` (Decimal) and `last_payment_date` (date|None).
    """
    from decimal import Decimal
    from django.db.models import (
        Q, Sum, Case, When, F, DecimalField, Value, Max, OuterRef, Subquery,
    )
    from django.db.models.functions import Coalesce

    from apps.members.models import Member

    # Last payment date per member (subquery — avoids GROUP BY issues on SQLite)
    last_pay_sq = (
        Payment.objects.filter(member=OuterRef("pk"))
        .order_by("-created_at")
        .values("created_at")[:1]
    )

    qs = (
        Member.objects.filter(is_active=True)
        .annotate(
            annotated_balance=Coalesce(
                Sum(
                    Case(
                        When(ledger_entries__direction=Direction.DEBIT,  then=F("ledger_entries__amount")),
                        When(ledger_entries__direction=Direction.CREDIT, then=-F("ledger_entries__amount")),
                        output_field=DecimalField(max_digits=14, decimal_places=2),
                    )
                ),
                Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2)),
            ),
            last_payment_date=Subquery(last_pay_sq),
        )
        .filter(annotated_balance__gt=0)
        .order_by("-annotated_balance")
    )

    if search:
        qs = qs.filter(
            Q(member_code__icontains=search) | Q(phone__icontains=search)
            | Q(first_name__icontains=search) | Q(last_name__icontains=search)
        )

    return qs
