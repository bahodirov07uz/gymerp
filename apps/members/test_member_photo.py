"""A'zo profil rasmi (photo) uchun testlar: fallback avatar, yuklash,
5MB chegarasi, avtomatik kichraytirish va update-photo view.
"""
import io
import tempfile

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.loader import render_to_string
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.members.models import (
    MEMBER_PHOTO_MAX_SIZE,
    Member,
)

User = get_user_model()


def make_image_bytes(width, height, fmt="JPEG"):
    from PIL import Image

    img = Image.new("RGB", (width, height), color="red")
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


class MemberPhotoTests(TestCase):
    def setUp(self):
        self._media = tempfile.TemporaryDirectory()
        self._override = override_settings(MEDIA_ROOT=self._media.name)
        self._override.enable()
        self.addCleanup(self._override.disable)
        self.addCleanup(self._media.cleanup)
        self.member = Member.objects.create(
            member_code="M-000101",
            first_name="Ali",
            last_name="Valiyev",
            phone="+998901112233",
        )

    def test_fallback_avatar_renders_initials(self):
        html = render_to_string(
            "members/_avatar.html", {"member": self.member, "size": "w-8 h-8"}
        )
        self.assertIn("AV", html)
        self.assertNotIn("<img", html)
        self.assertNotIn("no-image", html)

    def test_photo_renders_img_with_url(self):
        self.member.photo.save(
            "ali.jpg", ContentFile(make_image_bytes(100, 100)), save=True
        )
        html = render_to_string(
            "members/_avatar.html", {"member": self.member, "size": "w-8 h-8"}
        )
        self.assertIn("<img", html)
        self.assertIn(self.member.photo.url, html)
        self.assertIn('loading="lazy"', html)

    def test_photo_too_large_raises_validation_error(self):
        big = SimpleUploadedFile(
            "huge.jpg",
            make_image_bytes(10, 10) + b"0" * (MEMBER_PHOTO_MAX_SIZE + 1),
            content_type="image/jpeg",
        )
        member = Member(
            member_code="M-000102",
            first_name="Sardor",
            last_name="Karimov",
            phone="+998901112244",
            photo=big,
        )
        with self.assertRaises(ValidationError) as ctx:
            member.full_clean()
        self.assertIn("photo", ctx.exception.message_dict)

    def test_large_image_resized_on_save(self):
        self.member.photo.save(
            "big.jpg", ContentFile(make_image_bytes(1200, 900)), save=True
        )
        from PIL import Image

        with Image.open(self.member.photo.path) as img:
            self.assertLessEqual(max(img.size), 400)

    def test_update_photo_view_success(self):
        user = User.objects.create_user(username="photo-staff", password="password123")
        self.client.force_login(user)
        small = SimpleUploadedFile(
            "new.jpg", make_image_bytes(100, 100), content_type="image/jpeg"
        )
        resp = self.client.post(
            reverse("members:update_photo", args=[self.member.pk]),
            {"photo": small},
        )
        self.assertEqual(resp.status_code, 302)
        self.member.refresh_from_db()
        self.assertTrue(bool(self.member.photo))

    def test_update_photo_view_rejects_oversized(self):
        user = User.objects.create_user(username="photo-staff2", password="password123")
        self.client.force_login(user)
        big = SimpleUploadedFile(
            "huge.jpg",
            make_image_bytes(10, 10) + b"0" * (MEMBER_PHOTO_MAX_SIZE + 1),
            content_type="image/jpeg",
        )
        resp = self.client.post(
            reverse("members:update_photo", args=[self.member.pk]),
            {"photo": big},
        )
        self.assertEqual(resp.status_code, 302)
        self.member.refresh_from_db()
        self.assertFalse(bool(self.member.photo))

    def test_member_create_with_photo(self):
        user = User.objects.create_user(username="photo-staff3", password="password123")
        self.client.force_login(user)
        small = SimpleUploadedFile(
            "new.jpg", make_image_bytes(100, 100), content_type="image/jpeg"
        )
        resp = self.client.post(
            reverse("members:create"),
            {
                "first_name": "Madina",
                "last_name": "Karimova",
                "phone": "+998901112255",
                "photo": small,
            },
        )
        self.assertEqual(resp.status_code, 302)
        created = Member.objects.get(phone="+998901112255")
        self.assertTrue(bool(created.photo))
