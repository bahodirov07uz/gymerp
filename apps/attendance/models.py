from django.conf import settings
from django.db import models


class Attendance(models.Model):
    member = models.ForeignKey("members.Member", on_delete=models.CASCADE, related_name="attendances")
    date = models.DateField()
    check_in = models.DateTimeField()
    check_out = models.DateTimeField(null=True, blank=True)
    membership = models.ForeignKey(
        "memberships.Membership", null=True, blank=True, on_delete=models.SET_NULL, related_name="attendances"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-date", "-check_in"]
        indexes = [models.Index(fields=["member", "date"])]
        constraints = [
            # One OPEN (unchecked-out) session per member at a time.
            # Closed sessions (check_out IS NOT NULL) are unlimited.
            models.UniqueConstraint(
                fields=["member"],
                condition=models.Q(check_out__isnull=True),
                name="unique_open_attendance_per_member",
            ),
        ]

    def __str__(self):
        return f"{self.member} - {self.date} {self.check_in.strftime('%H:%M')}"
