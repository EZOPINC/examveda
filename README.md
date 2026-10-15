# WBPSC Mock Exam Platform

A Django modular monolith for free WBPSC exam preparation materials and future mock examinations. The approved architecture, reserved module names, and phase gates are documented in [ARCHITECTURE.md](ARCHITECTURE.md), [PROJECT_AI_RULES.md](PROJECT_AI_RULES.md), and [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md).

## Runtime baseline

The baseline is Python 3.13, Django 5.2.18 LTS, Psycopg 3.3.6, and PostgreSQL 18.6 for local verification. Package versions are pinned in `requirements.txt`; do not silently upgrade them.

## Local setup

Run PowerShell commands from the repository root:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `DJANGO_SECRET_KEY` and the PostgreSQL values in the ignored `.env`. Create a local PostgreSQL role and database first; the role needs permission to create temporary test databases when running Django's test runner. The application does not load `.env` automatically. Set values in the process environment before invoking Django, or use environment variables in the IDE run configuration. Never commit `.env`.

```powershell
$env:DJANGO_SETTINGS_MODULE = "config.settings.development"
# Set DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, and DJANGO_SECRET_KEY in this process.
python manage.py check --database default
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/`, `/free-resources/`, or `/admin/`. Development settings may use SQLite if `DB_NAME` is unset; PostgreSQL is the intended application database and must be used to verify PostgreSQL behavior. Tests create a separate temporary database.

## Content editorial workflow

1. Sign in to `/admin/` with an authorized staff account.
2. Create a page in **Content pages**, enter its English or Bengali title/body, summary, and SEO fields, then save it as a draft.
3. Use **Preview page** on the saved page. The route requires staff authentication and the content view permission; it shows a draft without publishing it.
4. Add optional exam, stage, year, resource type, subject, and topic classification in the **Resource metadata** inline. Upload PDFs separately under **Resource files** and choose public or restricted visibility.
5. To publish, check **Is published** and save. A publication timestamp is set if missing. The page then appears in matching public listings and its stable URL. A complete exam resource URL needs category, stage, year, type, and page slug.
6. Edit the same page to update it and keep the slug stable after publication. To unpublish, clear **Is published** and save. Public page and file routes then return not found. Restricted PDFs have no delivery endpoint in this phase.

Public PDF display is a browser convenience; viewers can still save, print, screenshot, or copy documents. Uploaded files are stored beneath `MEDIA_ROOT`; production web-server configuration must not expose that directory directly.

## Verification commands

```powershell
python manage.py check
python manage.py check --database default
python manage.py test content config
python manage.py makemigrations --check --dry-run
```

The Phase 2 content journey, permissions, stable routes, and publication rules are tested against PostgreSQL when PostgreSQL variables are configured in the process environment.
