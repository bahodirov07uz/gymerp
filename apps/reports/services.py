"""Aggregation queries backing the reports & dashboard screens.

All figures are computed directly from the ledger / payment / sale /
attendance tables via database aggregation -- never trusted from the
frontend and never duplicated into cached counters.
"""
import datetime
from decimal import Decimal

from django.db.models import Count, F, Q, Sum
from django.utils import timezone

from apps.attendance.models import Attendance
from apps.billing.models import Direction, LedgerTransaction, Payment, TransactionType
from apps.members.models import Member
from apps.memberships.models import Membership, MembershipStatus
from apps.products.models import Product
from apps.sales.models import ProductSale, ProductSaleItem


def _zero():
    return Decimal("0.00")


def revenue_for_range(start_date, end_date):
    """Revenue recognised = charges posted in the range (membership +
    daily + product), independent of whether they've been paid yet."""
    charges = LedgerTransaction.objects.filter(
        created_at__date__gte=start_date, created_at__date__lte=end_date,
        direction=Direction.DEBIT,
    )
    return {
        "membership_revenue": charges.filter(
            transaction_type__in=[TransactionType.MEMBERSHIP_CHARGE, TransactionType.DAILY_CHARGE]
        ).aggregate(t=Sum("amount"))["t"] or _zero(),
        "product_revenue": charges.filter(
            transaction_type=TransactionType.PRODUCT_CHARGE
        ).aggregate(t=Sum("amount"))["t"] or _zero(),
        "total_revenue": charges.aggregate(t=Sum("amount"))["t"] or _zero(),
    }


def payments_for_range(start_date, end_date):
    return Payment.objects.filter(
        created_at__date__gte=start_date, created_at__date__lte=end_date,
    ).aggregate(t=Sum("amount"))["t"] or _zero()


def attendance_for_range(start_date, end_date):
    return Attendance.objects.filter(date__gte=start_date, date__lte=end_date).count()


def new_members_for_range(start_date, end_date):
    return Member.objects.filter(
        created_at__date__gte=start_date, created_at__date__lte=end_date,
    ).count()


def total_outstanding_debt():
    """Sum of every member's positive balance, computed straight from
    the ledger (charges - payments), never a cached field."""
    totals = (
        LedgerTransaction.objects.values("member").annotate(
            charges=Sum("amount", filter=Q(direction=Direction.DEBIT)),
            payments=Sum("amount", filter=Q(direction=Direction.CREDIT)),
        )
    )
    debt = _zero()
    for row in totals:
        balance = (row["charges"] or _zero()) - (row["payments"] or _zero())
        if balance > 0:
            debt += balance
    return debt


def best_selling_products(start_date, end_date, limit=10):
    return (
        ProductSaleItem.objects.filter(
            sale__created_at__date__gte=start_date, sale__created_at__date__lte=end_date,
        )
        .values("product__id", "product__name")
        .annotate(quantity_sold=Sum("quantity"), revenue=Sum("line_total"))
        .order_by("-revenue")[:limit]
    )


def low_stock_products():
    return Product.objects.filter(is_active=True, stock_quantity__lte=F("low_stock_threshold"))


def dashboard_summary(as_of=None):
    as_of = as_of or timezone.localdate()
    month_start = as_of.replace(day=1)

    today_rev = revenue_for_range(as_of, as_of)
    month_rev = revenue_for_range(month_start, as_of)
    expiring = Membership.objects.filter(
        status=MembershipStatus.ACTIVE, end_date__gte=as_of,
        end_date__lte=as_of + datetime.timedelta(days=7),
    ).count()

    return {
        "active_members": Member.objects.filter(is_active=True).count(),
        "today_visitors": Attendance.objects.filter(date=as_of).count(),
        "today_revenue": today_rev["total_revenue"],
        "monthly_revenue": month_rev["total_revenue"],
        "outstanding_debt": total_outstanding_debt(),
        "active_memberships": Membership.objects.filter(status=MembershipStatus.ACTIVE).count(),
        "memberships_expiring_soon": expiring,
        "today_product_sales": ProductSale.objects.filter(created_at__date=as_of).count(),
        "low_stock_count": low_stock_products().count(),
    }
