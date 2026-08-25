from django.db import models
from django.urls import reverse


class Member(models.Model):
    GENDER_CHOICES = [("M", "Erkak"), ("F", "Ayol")]

    member_code = models.CharField(max_length=20, unique=True, db_index=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=32, db_index=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    address = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["first_name", "last_name"]
        indexes = [
            models.Index(fields=["phone"]),
            models.Index(fields=["member_code"]),
            models.Index(fields=["last_name", "first_name"]),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.member_code})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_absolute_url(self):
        return reverse("members:profile", args=[self.pk])

    @staticmethod
    def generate_member_code():
        """Sequential human-friendly code, e.g. M-000123."""
        last = Member.objects.order_by("-id").values_list("id", flat=True).first() or 0
        return f"M-{last + 1:06d}"
