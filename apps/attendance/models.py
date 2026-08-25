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
            models.UniqueConstraint(fields=["member", "date"], name="unique_attendance_per_member_per_day"),
        ]

    def __str__(self):
        return f"{self.member} - {self.date}"
