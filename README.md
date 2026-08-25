# Gym Management & Billing CRM

A production-oriented Django CRM that replaces notebook-based gym
management: members, daily/monthly memberships, attendance, sports
nutrition sales, inventory, payments, debt tracking, an auditable
financial ledger, and owner/manager reports.

## Tech stack

- **Backend:** Django 5 + Django REST Framework
- **Database:** PostgreSQL (SQLite supported for local/dev via `USE_SQLITE=True`)
- **Frontend:** Django templates + HTMX + Alpine.js + Tailwind CSS (via CDN, no build step)
- **Background jobs:** Celery + Redis (wired up, ready for future notification jobs)
- **Auth:** Django auth with a custom `User` model and OWNER / MANAGER / RECEPTIONIST roles
- Dockerized dev environment (Postgres + Redis + web + celery)

## Architecture

```
apps/
    accounts/     custom User model, roles, permission mixins
    members/      Member profile, search, reception landing page
    memberships/  MembershipPlan catalogue + Membership purchases
    attendance/   check-in / check-out, one-record-per-day guarantee
    products/     product catalogue (sports nutrition etc.)
    sales/        ProductSale / ProductSaleItem + atomic checkout service
    billing/      LedgerTransaction (source of truth) + Payment
    inventory/    StockMovement audit trail + adjust_inventory()
    reports/      daily/monthly/product aggregation queries
    audit/        AuditLog for every business-critical mutation
    dashboard/    owner/manager dashboard view
```

Business logic lives in each app's `services.py`, not in views or
templates. Key service functions:

- `apps.memberships.services.create_membership` / `create_daily_membership`
- `apps.attendance.services.check_in_member`
- `apps.sales.services.create_product_sale`
- `apps.billing.services.create_payment` / `calculate_member_balance`
- `apps.inventory.services.adjust_inventory`

### The financial ledger is the source of truth

`billing.LedgerTransaction` is an append-only table. Every membership
charge, daily-plan charge, product sale, manual charge, and payment is
written here. `Member` has **no** cached `balance` field — the balance
is always recomputed from the ledger
(`total_charges - total_payments`) so it can never silently drift out
of sync. Rows can never be edited or deleted (`save()`/`delete()`
raise on existing rows); corrections are made by posting a **reversal**
entry (`billing.services.reverse_transaction`), which only OWNER/MANAGER
roles can trigger.

## Getting started (Docker)

```bash
cp .env.example .env          # edit SECRET_KEY etc.
docker compose up --build
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py seed_demo   # optional demo data
```

App will be at http://localhost:8000 — reception screen at `/members/reception/`.

For a live-reloading dev server instead of gunicorn:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

## Getting started (local, no Docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export USE_SQLITE=True DJANGO_DEBUG=True
python manage.py migrate
python manage.py seed_demo      # creates owner/owner12345, reception/reception12345, demo members
python manage.py runserver
```

## Tests

```bash
python manage.py test apps
```

Covers: monthly/daily membership charges, duplicate daily-charge
prevention, product sale charge + stock decrement, insufficient-stock
rejection (whole sale rolled back), multi-product totals, payments and
partial payments, membership expiration, ledger atomicity/immutability,
and role-based permission enforcement (receptionist blocked from
reversing ledger entries or managing inventory).

## Roles

| Role | Access |
|---|---|
| OWNER | full access |
| MANAGER | members, memberships, products, payments, reports, inventory, financial reversals |
| RECEPTIONIST | members, attendance, product sales, payments — cannot reverse/delete financial records, change product cost, or touch settings |

## Notes / what's intentionally stubbed

- Telegram/SMS membership-expiry notifications: Celery is wired up but
  no notification task is implemented yet, per the spec ("do not
  automatically send until explicitly implemented").
- `expire_outdated_memberships()` (memberships/services.py) is ready to
  run as a daily Celery beat task or cron-triggered management command;
  wire it up via `python manage.py shell -c "from apps.memberships.services import expire_outdated_memberships; expire_outdated_memberships()"`.
