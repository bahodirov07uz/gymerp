from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.billing.services import calculate_member_balance
from apps.members.models import Member
from apps.memberships.models import Membership, MembershipStatus, MembershipPlan, PlanType
from apps.memberships.services import (
    create_daily_membership,
    create_membership,
    expire_outdated_memberships,
    get_active_membership,
)


class MembershipServiceTests(TestCase):
    def setUp(self):
        self.member = Member.objects.create(
            member_code="M-000001", first_name="Ali", last_name="Valiyev", phone="+998901112233",
        )
        self.monthly_plan = MembershipPlan.objects.create(
            name="Oylik", plan_type=PlanType.MONTHLY, price=Decimal("300000"), duration_days=30,
        )
        self.daily_plan = MembershipPlan.objects.create(
            name="Kunlik", plan_type=PlanType.DAILY, price=Decimal("20000"), duration_days=1,
        )

    def test_monthly_membership_creates_correct_charge(self):
        create_membership(member=self.member, plan=self.monthly_plan)
        self.assertEqual(calculate_member_balance(self.member), Decimal("300000.00"))
        membership = Membership.objects.get(member=self.member)
        self.assertEqual(membership.price_at_purchase, Decimal("300000"))
        self.assertEqual(membership.status, MembershipStatus.ACTIVE)

    def test_monthly_price_change_does_not_rewrite_history(self):
        create_membership(member=self.member, plan=self.monthly_plan)
        self.monthly_plan.price = Decimal("350000")
        self.monthly_plan.save()
        membership = Membership.objects.get(member=self.member)
        self.assertEqual(membership.price_at_purchase, Decimal("300000"))

    def test_daily_membership_creates_only_one_charge_per_day(self):
        today = timezone.localdate()
        m1, created1 = create_daily_membership(member=self.member, plan=self.daily_plan, day=today)
        m2, created2 = create_daily_membership(member=self.member, plan=self.daily_plan, day=today)

        self.assertTrue(created1)
        self.assertFalse(created2)
        self.assertEqual(m1.pk, m2.pk)
        self.assertEqual(calculate_member_balance(self.member), Decimal("20000.00"))
        self.assertEqual(Membership.objects.filter(member=self.member).count(), 1)

    def test_duplicate_daily_charge_is_prevented_across_calls(self):
        today = timezone.localdate()
        for _ in range(5):
            create_daily_membership(member=self.member, plan=self.daily_plan, day=today)
        self.assertEqual(Membership.objects.filter(member=self.member).count(), 1)
        self.assertEqual(calculate_member_balance(self.member), Decimal("20000.00"))

    def test_duplicate_active_monthly_membership_is_prevented(self):
        from apps.memberships.services import DuplicateMembershipError
        create_membership(member=self.member, plan=self.monthly_plan)
        with self.assertRaises(DuplicateMembershipError) as ctx:
            create_membership(member=self.member, plan=self.monthly_plan)
        self.assertIsNotNone(ctx.exception.existing_end_date)

    def test_membership_expiration_works(self):
        yesterday = timezone.localdate() - timezone.timedelta(days=40)
        # Bypasses active check since start_date is in past
        Membership.objects.create(
            member=self.member, plan=self.monthly_plan, start_date=yesterday,
            end_date=yesterday + timezone.timedelta(days=29), price_at_purchase=self.monthly_plan.price,
            status=MembershipStatus.ACTIVE,
        )
        updated = expire_outdated_memberships()
        self.assertEqual(updated, 1)
        membership = Membership.objects.get(member=self.member)
        self.assertEqual(membership.status, MembershipStatus.EXPIRED)
        self.assertIsNone(get_active_membership(self.member))
