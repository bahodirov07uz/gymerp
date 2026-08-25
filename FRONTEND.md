# GymCRM Frontend Design System

Ushbu hujjat — barcha Django shablonlari uchun birlamchi dizayn qoidanomasi.
Har bir yangi shablon yozishdan OLDIN shu hujjat o'qilishi va QATIY AMAL
QILINISHI shart. Chetga chiqish — xato hisoblanadi.

---

## 1. Rang Palitrasi

### Asosiy ranglar

| Token            | Tailwind sinfi        | Hex / qiymat            | Maqsad                                  |
|------------------|-----------------------|-------------------------|-----------------------------------------|
| --bg             | bg-[#0D0F12]          | #0D0F12                 | Sahifa foni (eng quyuq)                 |
| --surface        | bg-[#13161B]          | #13161B                 | Karta foni (birlamchi panel)            |
| --surface-2      | bg-[#1A1E25]          | #1A1E25                 | Yuqori turuvchi panel / input foni      |
| --border         | border-[#252A33]      | #252A33                 | Barcha chegaralar                       |
| --text           | text-[#F0F2F5]        | #F0F2F5                 | Asosiy matn                             |
| --muted          | text-[#8A919E]        | #8A919E                 | Ikkinchi darajali matn / label          |
| --accent-green   | text-emerald-400      | #34D399                 | Muvaffaqiyat / to'lov / faol            |
| --accent-red     | text-red-400          | #F87171                 | Xato / qarz / bloklangan               |
| --accent-amber   | text-amber-400        | #FBBF24                 | Ogohlantirish / muddat yaqin            |
| --accent-blue    | text-sky-400          | #38BDF8                 | Ma'lumot / qidiruv / link              |
| --primary        | bg-emerald-600        | #059669                 | Tugmalar, CTA                           |

TAQIQLANGAN: Generic blue-purple gradient, oq fon karta uchun, tasodifiy ranglar.

---

## 2. Tipografiya Shkalasi

Shrift: Inter (Google Fonts CDN)

| Daraja   | Tailwind sinflari                              | Ishlatilish joyi                     |
|----------|------------------------------------------------|--------------------------------------|
| h1       | text-2xl font-bold text-[#F0F2F5]              | Sahifa sarlavhasi                    |
| h2       | text-lg font-semibold text-[#F0F2F5]           | Karta sarlavhasi                     |
| h3       | text-sm font-semibold text-[#F0F2F5]           | Kichik blok sarlavhasi               |
| body     | text-sm text-[#F0F2F5]                         | Oddiy matn                           |
| small    | text-xs text-[#8A919E]                         | Meta-ma'lumot                        |
| label    | text-xs font-medium text-[#8A919E] uppercase   | Form label, KPI label                |
| number   | text-xl font-bold tabular-nums text-[#F0F2F5]  | KPI raqamlari                        |

---

## 3. Bo'sh Joy Tizimi (Spacing Scale)

4px asosida: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64

| Kontekst                        | Qiymat                          |
|---------------------------------|---------------------------------|
| Karta ichki padding             | p-4 yoki p-5                    |
| Kartalar orasidagi masofa       | gap-4                           |
| Jadval qatori padding           | px-4 py-3                       |
| Tugma padding                   | px-4 py-2 (normal)              |
| Sahifa tashqi padding           | px-4 sm:px-6 lg:px-8            |
| Sidebar kenglik                 | w-56 (224px) fixed              |
| KPI grid                        | grid-cols-2 sm:grid-cols-4 gap-4|

---

## 4. Status Badge Uslublari (YAGONA)

- Faol: bg-emerald-500/10 text-emerald-400 border-emerald-500/20
- Qarz: bg-red-500/10 text-red-400 border-red-500/20
- Ogohlantirish: bg-amber-500/10 text-amber-400 border-amber-500/20
- Zalda: bg-sky-500/10 text-sky-400 border-sky-500/20
- Tugagan: bg-[#1A1E25] text-[#8A919E] border-[#252A33]

---

## 5. Emoji Qoidasi

RUXSAT: funksional signallar uchun faqat: ss (Check in), 🚪 (Chiqish), 💳 (Qarz), 
warning (Ogohlantirish), ⏳ (Muddat yaqin), 🧾 (Hisob-kitob)

TAQIQLANGAN (AI dust): 🚀 ✨ 🎉 😊 👍 💪 🏋️ 🌟 🔥 va boshqa dekorativ emoji.

Qoida: emoji DOIM matn bilan birga, HECH QACHON yolg'iz.

---

## 6. Responsive Qoidalar

- Mobile (< 640px): 1 ustun, vertikal stack
- Tablet (640-1024): sm: prefikslari, sidebar yashiq
- Desktop (> 1024): lg: prefikslari, sidebar ko'rinadi

Reception ekrani planshetda BIRINCHI PRIORITET.

---

## 7. HTMX Animatsiyalar

- hx-swap="innerHTML transition:true" — barcha inline yangilanishlar
- hx-trigger="keyup changed delay:300ms" — qidiruv input
- hx-indicator="#spinner-id" — har bir so'rovda ko'rsatish
- Alpine x-transition: enter/leave 100-150ms ease-out/in

---

## 8. Navigation

Sidebar (desktop fixed w-56): Dashboard, A'zolar, Qabul, Qarzdorlar, Ombor, 
Hisobotlar (kunlik/oylik/mahsulot/muddatlar), Chiqish

Mobile: hamburger + logo top-bar

---

## 9. Kartalar

Standart: bg-[#13161B] border border-[#252A33] rounded-xl p-5
Elevated: bg-[#1A1E25] border border-[#252A33] rounded-xl shadow-xl shadow-black/40

---

## 10. Real Ma'lumot Qoidasi

- HECH QACHON "Lorem ipsum" yoki "No data" — o'zbek tilida real kontekst
- Bo'sh holatlar: "Hozircha hech kim zalda yo'q", "A'zolar topilmadi"
- Raqamlar: {{ amount|intcomma }} UZS
- Sanalar: {{ date|date:"d-M-Y" }}
