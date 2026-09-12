"""Admin panel o'zbekchalash + asosiy sahifalardagi Admin tugma testlari."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class AdminUzbekTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_superuser(
            username="admin_uz", password="password123", email="a@a.uz"
        )

    def test_admin_index_is_uzbek(self):
        self.client.force_login(self.owner)
        resp = self.client.get(reverse("admin:index"))
        self.assertEqual(resp.status_code, 200)
        for text in [
            "GymCRM",  # branding
            "Boshqaruv paneli",  # index_title
            "A&#x27;zolar",  # members app/model (HTML entity)
            "Foydalanuvchilar",  # accounts app
            "Davomat",
            "Mahsulotlar",
            "Moliya",
        ]:
            self.assertContains(resp, text)
        self.assertNotContains(resp, "Site administration")

    def test_admin_login_page_is_uzbek(self):
        resp = self.client.get(reverse("admin:login"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Kirish")
        self.assertContains(resp, "Foydalanuvchi nomi")

    def test_member_add_page_buttons_and_labels_uzbek(self):
        self.client.force_login(self.owner)
        resp = self.client.get(reverse("admin:members_member_add"))
        self.assertEqual(resp.status_code, 200)
        for text in [
            "Saqlash va tahrirlashni davom ettirish",
            "Saqlash va yangisini qo'shish",
            "A&#x27;zo kodi",  # label matnida apostrof entity bo'ladi
            "Tug&#x27;ilgan sana",
            "Profil rasmi",
        ]:
            self.assertContains(resp, text)
        self.assertNotContains(resp, "Save and continue editing")

    def test_user_change_page_labels_uzbek(self):
        user = User.objects.create_user(username="oddiy", password="password123")
        self.client.force_login(self.owner)
        resp = self.client.get(reverse("admin:accounts_user_change", args=[user.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Rol va kontakt")
        self.assertContains(resp, "Qabulxona xodimi")
        self.assertContains(resp, "Foydalanuvchilar")


class AdminButtonTests(TestCase):
    def test_staff_sees_admin_button(self):
        staff = User.objects.create_user(username="staff1", password="password123")
        staff.is_staff = True
        staff.save()
        self.client.force_login(staff)
        resp = self.client.get(reverse("dashboard:index"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Admin panel")
        self.assertContains(resp, reverse("admin:index"))

    def test_non_staff_sees_no_admin_button(self):
        plain = User.objects.create_user(username="plain1", password="password123")
        self.assertFalse(plain.is_staff)
        self.client.force_login(plain)
        resp = self.client.get(reverse("dashboard:index"))
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Admin panel")
