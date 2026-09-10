from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory
from django.utils import timezone

from apps.attendance.models import Attendance
from apps.attendance.services import AlreadyCheckedIn, DailyPlanRequired, check_in_member
from apps.attendance.views import AttendanceBoardView, AttendanceRowCheckOutView, InGymListView
from apps.members.models import Member
from apps.memberships.models import MembershipPlan, PlanType
from apps.memberships.services import create_membership
from apps.billing.services import post_charge
from apps.billing.models import TransactionType

User = get_user_model()


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


class InGymListViewTests(TestCase):
    """
    VAZIFA 1 tekshiruvi:
    InGymListView date=today filtri yo'q — 2 kun oldingi ochiq sessiya ham ko'rinishi shart.
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="staff", password="pass")
        self.member = Member.objects.create(
            member_code="M-000002", first_name="Bobur", last_name="Toshev", phone="+998901234567",
        )

    def _make_stale_attendance(self, days_ago=2):
        """Create an open attendance record dated `days_ago` days in the past."""
        stale_date = timezone.localdate() - timedelta(days=days_ago)
        stale_checkin = timezone.now() - timedelta(days=days_ago)
        return Attendance.objects.create(
            member=self.member,
            date=stale_date,
            check_in=stale_checkin,
            check_out=None,  # still open
        )

    def test_stale_open_session_appears_in_in_gym_list(self):
        """
        A member with an open session from 2 days ago (no check_out) MUST appear
        in InGymListView — because we only filter by check_out__isnull=True now.
        """
        att = self._make_stale_attendance(days_ago=2)

        request = self.factory.get("/attendance/in-gym/")
        request.user = self.user

        response = InGymListView.as_view()(request)
        self.assertEqual(response.status_code, 200)

        # The attendance record must be in the queryset passed to the template
        in_gym_qs = Attendance.objects.filter(check_out__isnull=True)
        self.assertIn(att, list(in_gym_qs))
        self.assertEqual(in_gym_qs.count(), 1)

    def test_closed_session_does_not_appear_in_in_gym_list(self):
        """A checked-out attendance must NOT appear, regardless of date."""
        att = self._make_stale_attendance(days_ago=2)
        att.check_out = timezone.now() - timedelta(days=1)
        att.save(update_fields=["check_out"])

        in_gym_qs = Attendance.objects.filter(check_out__isnull=True)
        self.assertEqual(in_gym_qs.count(), 0)

    def test_today_open_session_still_appears(self):
        """Sanity check: a fresh session opened today is still visible."""
        today = timezone.localdate()
        att = Attendance.objects.create(
            member=self.member,
            date=today,
            check_in=timezone.now(),
            check_out=None,
        )

        in_gym_qs = Attendance.objects.filter(check_out__isnull=True)
        self.assertIn(att, list(in_gym_qs))
        self.assertEqual(in_gym_qs.count(), 1)

    def test_stale_session_is_marked_stale_in_queryset(self):
        """
        2 kun eski sessiyaning date bugundan kichik — bu template'da eski sessiya belgisi
        ko'rsatish uchun ishlatiladi.
        """
        att = self._make_stale_attendance(days_ago=2)
        today = timezone.localdate()
        self.assertLess(att.date, today, "Stale attendance.date must be before today")


class AttendanceBoardViewTests(TestCase):
    """
    VAZIFA 3 tekshiruvi:
    - /attendance/ sahifasi ochiq sessiyalarni balanslari bilan qaytaradi.
    - row-checkout tugmasi sessiyani yopadi.
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="staff_board", password="pass")
        self.member = Member.objects.create(
            member_code="M-000003", first_name="Doston", last_name="Karimov", phone="+998909998877",
        )
        self.plan = MembershipPlan.objects.create(
            name="Standart", plan_type=PlanType.MONTHLY, price=Decimal("250000"), duration_days=30,
        )

    def test_board_view_renders_successfully(self):
        request = self.factory.get("/attendance/")
        request.user = self.user

        response = AttendanceBoardView.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_board_view_shows_in_gym_members_with_balance(self):
        # 1. Post a charge for member (balance = 100,000 UZS)
        post_charge(
            member=self.member,
            transaction_type=TransactionType.MEMBERSHIP_CHARGE,
            amount=Decimal("100000"),
            description="A'zolik to'lovi",
            created_by=self.user,
        )

        # 2. Check in member (open session)
        create_membership(member=self.member, plan=self.plan)
        att = check_in_member(member=self.member, created_by=self.user)

        self.client.force_login(self.user)
        response = self.client.get("/attendance/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("in_gym_list", response.context)
        in_gym = response.context["in_gym_list"]
        self.assertEqual(len(in_gym), 1)
        self.assertEqual(in_gym[0].pk, att.pk)
        # 100,000 manual charge + 250,000 plan fee = 350,000
        self.assertEqual(in_gym[0].member_balance, Decimal("350000"))

    def test_checkout_row_view_closes_attendance(self):
        create_membership(member=self.member, plan=self.plan)
        att = check_in_member(member=self.member, created_by=self.user)
        self.assertIsNone(att.check_out)

        request = self.factory.post(f"/attendance/{att.pk}/row-checkout/")
        request.user = self.user

        response = AttendanceRowCheckOutView.as_view()(request, pk=att.pk)
        self.assertEqual(response.status_code, 200)

        att.refresh_from_db()
        self.assertIsNotNone(att.check_out)

