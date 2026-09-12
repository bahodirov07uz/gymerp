"""Member bottom-sheet modal mobil regressiya testlari.

Muammo: mobilda "Mahsulot sotish" qidiruvida member card yopilib qolgan.
Kutilma: karta ICHIDAGI har qanday HTMX swap (jumladan product-search)
modalni ochiq tasdiqlaydi; hech qanday swap uni avtomatik yopmaydi.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class MemberModalMarkupTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="modal-staff", password="password123")
        self.client.force_login(self.user)

    def test_reception_modal_reaffirms_open_on_inner_swaps(self):
        resp = self.client.get(reverse("members:reception"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        # Karta ichidagi swap (masalan #product-search-results) ham open=true qiladi.
        self.assertIn("contains($event.detail.target)", html)
        # Hech qanday auto-close ternary bo'lmasligi kerak.
        self.assertNotIn("? open = true : open = false", html)
        # Body scroll-lock mexanizmi ulangan.
        self.assertIn("member-modal-open", html)

    def test_board_modal_reaffirms_open_on_inner_swaps(self):
        resp = self.client.get(reverse("attendance:board"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn("contains($event.detail.target)", html)
        self.assertNotIn("? open = true : open = false", html)
        self.assertIn("member-modal-open", html)

    def test_viewport_handles_mobile_keyboard(self):
        resp = self.client.get(reverse("members:reception"))
        self.assertIn("interactive-widget=resizes-content", resp.content.decode())
