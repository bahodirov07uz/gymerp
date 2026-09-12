from django.conf import settings
from django.db import models


class Attendance(models.Model):
    member = models.ForeignKey("members.Member", verbose_name="A'zo", on_delete=models.CASCADE, related_name="attendances")
    date = models.DateField("Sana")
    check_in = models.DateTimeField("Kirish vaqti")
    check_out = models.DateTimeField("Chiqish vaqti", null=True, blank=True)
    membership = models.ForeignKey(
        "memberships.Membership", verbose_name="A'zolik", null=True, blank=True, on_delete=models.SET_NULL, related_name="attendances"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Yaratgan", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-date", "-check_in"]
        verbose_name = "Davomat yozuvi"
        verbose_name_plural = "Davomat yozuvlari"
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
