# Perfume Store

A practice project for learning Django and Django REST Framework. Django templates
render the storefront, and a JavaScript cart calls authenticated JSON endpoints to
check stock and submit a practice purchase.

## Features

- Registration, login, and logout using Django's authentication system.
- Product search, stock filtering, and sorting by name or price.
- An in-memory browser cart with editable quantities and a total.
- Checkout validation and atomic stock updates.
- Order confirmation email, printed to the terminal by default.
- Staff-only product creation with optional image uploads.
- Django admin with name search, editable stock, and price range filtering.

## Stack

Python 3.13, Django 5.2, Django REST Framework, Bootstrap 5, and vanilla JavaScript.
SQLite is the default for a fresh checkout; PostgreSQL is also supported.

## Run locally

These commands use PowerShell from the project folder. Python 3.13 must be installed.
Calling the virtual environment's Python directly avoids activation policy issues.

```powershell
py -3.13 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Paste the generated key into `DJANGO_SECRET_KEY` in `.env`, enclosed in double quotes.
Copy `.env.example` only when you do not already have a `.env`; keep your existing
local settings when updating this project. Environment variables take precedence
over values in `.env`.

```powershell
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py createsuperuser
.\venv\Scripts\python.exe manage.py runserver
```

Open <http://127.0.0.1:8000/>. Add products in `/admin/`, or use `/add/` while logged
in as staff. Register a customer account to browse `/products/` and try the cart.
New installations start with no products or customer accounts. Uploaded images and
database contents are local data and are excluded from Git.

## PostgreSQL

Create an empty database in PostgreSQL, then configure `.env`:

```dotenv
DB_ENGINE=postgresql
DB_NAME=perfume_db
DB_USER=postgres
DB_PASSWORD="your-local-database-password"
DB_HOST=localhost
DB_PORT=5432
```

Run `manage.py migrate` using the virtual environment's Python. Switching database
engines does not copy existing data. The cleanup preserved this workspace's original
PostgreSQL settings in its ignored `.env`.

## Email

The console backend prints confirmation messages in the terminal. It does not send
real email. To enable SMTP, set these values in `.env`:

```dotenv
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER="your-email@example.com"
EMAIL_HOST_PASSWORD="your-provider-app-password"
DEFAULT_FROM_EMAIL="your-email@example.com"
```

Use credentials appropriate for your email provider. If email fails after checkout,
the stock deduction remains completed and the API returns `confirmation_sent: false`.
It does not ask the browser to repeat the purchase.

## API

Both endpoints use Django session authentication. Log in at `/login/` first. POST
requests must include the session cookie and an `X-CSRFToken` header. The store page
issues a CSRF token and the cart sends it automatically. Anonymous API requests
return JSON with status 403. This follows DRF's
[session authentication requirements](https://www.django-rest-framework.org/api-guide/authentication/#sessionauthentication).

| Method | URL | Purpose |
| --- | --- | --- |
| POST | `/api/stock/` | Return the current stock of a perfume |
| POST | `/api/buy/` | Validate a cart, deduct stock, and send a confirmation |

Stock request:

```json
{"id": 1}
```

Stock response:

```json
{"stock": 5}
```

Purchase request (replace the ID with an existing product ID):

```json
{
  "email": "buyer@example.com",
  "cart": [{"id": 1, "quantity": 2}]
}
```

Purchase response:

```json
{
  "message": "Order placed successfully! Confirmation sent to your email.",
  "total": "41.00",
  "confirmation_sent": true
}
```

The server calculates the total from database prices. Empty carts, duplicate product
IDs, nonpositive quantities, and invalid emails return 400. Missing products return
404; insufficient stock returns 400. Any rejected cart leaves the entire inventory
unchanged. Carts contain at most 100 distinct products.

## Tests

```powershell
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py test --settings=perfumestore.test_settings
.\venv\Scripts\python.exe manage.py makemigrations --check --dry-run --settings=perfumestore.test_settings
```

The test settings use an isolated SQLite database and in-memory email, so tests do
not need PostgreSQL or send real messages. The tests cover account flows, permissions,
CSRF, storefront filtering, admin price filtering, checkout validation, stock updates,
and email failure. GitHub Actions runs checks and tests on pushes and pull requests.

For database-specific tests against a local PostgreSQL test database:

```powershell
.\venv\Scripts\python.exe manage.py test
```

Django creates and destroys a separate test database; the PostgreSQL user needs
permission to create it. Do not point this learning app at a production database.

## Optional debug toolbar

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Set `DJANGO_DEBUG_TOOLBAR=True` and keep `DJANGO_DEBUG=True` in `.env`. The toolbar is
disabled by default. Custom SQL-printing middleware has been removed; the toolbar
provides query inspection when needed.

## Project layout

```text
perfumestore/       Django settings, routing, and test settings
perfumes/          Model, forms, serializers, views, checkout service, and tests
templates/         Storefront and admin templates
static/            Images, cart JavaScript, and stylesheet
.github/workflows/ Automated checks
```

## Learning project scope

Purchases are demonstrations: there is no payment processing, shipping integration,
saved order model, or order history. The cart resets on page reload. Checkout does
not provide idempotency keys; after a lost response, inspect stock before retrying.
Production hosting, HTTPS, rate limiting, and media storage are future work.

Product images supplied with the original project are demo assets. Their original
source and redistribution permissions are not documented. No license is assigned
to third-party assets by this repository.

