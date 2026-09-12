import logging
import os

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse

logger = logging.getLogger(__name__)

# Profil rasmi uchun maksimal hajm (5 MB) — serverni katta fayllardan himoya qiladi.
MEMBER_PHOTO_MAX_SIZE = 5 * 1024 * 1024
# Saqlashda rasmning katta tomoni shu o'lchamdan oshmasligi kerak (px).
MEMBER_PHOTO_MAX_DIMENSION = 400


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
    photo = models.ImageField(upload_to="members/%Y/%m/", blank=True, null=True)
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

    def clean(self):
        super().clean()
        photo = self.photo
        if photo and getattr(photo, "name", None):
            try:
                size = photo.size
            except (ValueError, OSError, AttributeError):
                size = None
            if size is not None and size > MEMBER_PHOTO_MAX_SIZE:
                raise ValidationError({
                    "photo": "Rasm hajmi 5MB dan oshmasligi kerak.",
                })

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._resize_photo_if_needed()

    def _resize_photo_if_needed(self):
        """Katta yuklangan rasmlarni saqlashda 400px gacha kichraytiradi.

        Hech qachon saqlashni buzmasligi kerak — har qanday xatoda
        original fayl o'z holicha qoladi.
        """
        if not self.photo or not getattr(self.photo, "name", None):
            return
        try:
            path = self.photo.path
        except (ValueError, NotImplementedError):
            return
        if not path or not os.path.exists(path):
            return
        try:
            from PIL import Image

            try:
                resample = Image.Resampling.LANCZOS
            except AttributeError:  # Pillow < 9.1
                resample = Image.LANCZOS

            with Image.open(path) as img:
                if max(img.size) <= MEMBER_PHOTO_MAX_DIMENSION:
                    return
                img.thumbnail(
                    (MEMBER_PHOTO_MAX_DIMENSION, MEMBER_PHOTO_MAX_DIMENSION),
                    resample,
                )
                ext = os.path.splitext(path)[1].lower()
                if ext in (".jpg", ".jpeg") or (img.format or "").upper() in ("JPEG", "JPG"):
                    if img.mode in ("RGBA", "LA", "P"):
                        img = img.convert("RGB")
                    img.save(path, format="JPEG", quality=85, optimize=True)
                else:
                    img.save(path, optimize=True)
        except Exception:
            logger.warning("Member %s rasmini kichraytirib bo'lmadi.", self.pk, exc_info=True)

    def get_absolute_url(self):
        return reverse("members:profile", args=[self.pk])

    @staticmethod
    def generate_member_code():
        """Sequential human-friendly code, e.g. M-000123."""
        last = Member.objects.order_by("-id").values_list("id", flat=True).first() or 0
        return f"M-{last + 1:06d}"
