from django.db import models
from django.core.exceptions import ValidationError


class PlanType(models.TextChoices):
    DAILY = "DAILY", "Kunlik"
    MONTHLY = "MONTHLY", "Oylik"


class MembershipPlan(models.Model):
    """Configurable pricing catalogue. Never hardcode prices in code."""

    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=10, choices=PlanType.choices)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    duration_days = models.PositiveIntegerField(help_text="1 for daily plans, e.g. 30 for monthly.")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["plan_type", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_plan_type_display()}) - {self.price} UZS"


class MembershipStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Faol"
    EXPIRED = "EXPIRED", "Muddati tugagan"
    CANCELLED = "CANCELLED", "Bekor qilingan"


class Membership(models.Model):
    """A purchased membership period. Stores the price actually paid so
    that later catalogue price changes never rewrite history."""

    member = models.ForeignKey("members.Member", on_delete=models.CASCADE, related_name="memberships")
    plan = models.ForeignKey(MembershipPlan, on_delete=models.PROTECT, related_name="memberships")
    start_date = models.DateField()
    end_date = models.DateField()
    price_at_purchase = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, choices=MembershipStatus.choices, default=MembershipStatus.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["member", "status"]),
            models.Index(fields=["end_date"]),
        ]

    def __str__(self):
        return f"{self.member} - {self.plan.name} ({self.start_date}..{self.end_date})"

    def clean(self):
        if self.end_date < self.start_date:
            raise ValidationError("end_date must not be before start_date.")
