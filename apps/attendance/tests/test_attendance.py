from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.attendance.models import Attendance
from apps.attendance.services import AlreadyCheckedIn, DailyPlanRequired, check_in_member
from apps.members.models import Member
from apps.memberships.models import MembershipPlan, PlanType
from apps.memberships.services import create_membership


class AttendanceServiceTests(TestCase):
    def setUp(self):
        self.member = Member.objects.create(
            member_code="M-000001", first_name="Ali", last_name="Valiyev", phone="+998901112233",
        )
        self.monthly_plan = MembershipPlan.objects.create(
            name="Oylik", plan_type=PlanType.MONTHLY, price=Decimal("300000"), duration_days=30,
        )

    def test_check_in_requires_active_membership(self):
        with self.assertRaises(DailyPlanRequired):
            check_in_member(member=self.member)

    def test_check_in_succeeds_with_active_membership(self):
        create_membership(member=self.member, plan=self.monthly_plan)
        attendance = check_in_member(member=self.member)
        self.assertEqual(Attendance.objects.filter(member=self.member).count(), 1)
        self.assertEqual(attendance.date, timezone.localdate())

    def test_duplicate_checkin_prevented_while_open_session_exists(self):
        create_membership(member=self.member, plan=self.monthly_plan)
        check_in_member(member=self.member)
        with self.assertRaises(AlreadyCheckedIn):
            check_in_member(member=self.member)
        self.assertEqual(Attendance.objects.filter(member=self.member).count(), 1)

    def test_multiple_checkins_allowed_after_checkout_on_same_day(self):
        from apps.attendance.services import check_out_member
        today = timezone.localdate()
        create_membership(member=self.member, plan=self.monthly_plan)

        # 1st session: in -> out
        att1 = check_in_member(member=self.member)
        self.assertIsNone(att1.check_out)
        check_out_member(attendance=att1)
        self.assertIsNotNone(att1.check_out)

        # 2nd session: in -> out on the same day
        att2 = check_in_member(member=self.member)
        self.assertIsNone(att2.check_out)
        check_out_member(attendance=att2)
        self.assertIsNotNone(att2.check_out)

        # 3rd session: in (currently open)
        att3 = check_in_member(member=self.member)
        self.assertIsNone(att3.check_out)

        self.assertEqual(Attendance.objects.filter(member=self.member, date=today).count(), 3)
        self.assertEqual(Attendance.objects.filter(member=self.member, check_out__isnull=True).count(), 1)
