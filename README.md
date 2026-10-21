# WBPSC Mock Exam Platform

A Django modular monolith for free WBPSC exam preparation materials and future mock examinations. The approved architecture, reserved module names, and phase gates are documented in [ARCHITECTURE.md](ARCHITECTURE.md), [PROJECT_AI_RULES.md](PROJECT_AI_RULES.md), and [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md).

## Runtime baseline

The baseline is Python 3.13, Django 5.2.18 LTS, Psycopg 3.3.6, Gunicorn 26.2.0 for Linux deployment, and PostgreSQL 18.6 for local verification. Package versions are pinned in `requirements.txt`; do not silently upgrade them.

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

## Mock exams (Phase 3)

Authorized staff create questions and mock tests in `/admin/`. A question must have at least two options and exactly one correct option before it can be included in a test. Published tests need at least one valid question. After the first attempt starts, test identity and scoring content are frozen; create new question and test records for revisions. Staff may still unpublish a test or close its availability window to stop new starts.

Students can browse `/mock-tests/` without signing in. Django's built-in login is at `/accounts/login/`; public student registration is at `/accounts/register/`. A signed-in student can view `/accounts/profile/`, change their email or password, start a test, resume the active attempt until its server deadline, autosave answers, and submit. Expiry finalizes saved answers automatically when an attempt endpoint observes the deadline. Scores and answer explanations become available after submission or expiry. Attempts are unlimited, and the timer in the browser is only a display aid. Lost-password recovery is administrator-assisted after identity verification until verified-email recovery and production mail delivery are approved.

## Accounts and access policies (Phase 4)

Registration uses Django's built-in user model and creates ordinary student accounts only. It cannot assign staff status, groups, or permissions. Administrators grant staff access through Django admin or trusted operator commands. Authenticated students can view/update only their own account email and change their password; attempt pages remain owner-scoped. Django admin requires an active staff account and the relevant model permission.

`access_control.services.user_can_access()` is the shared server-side policy for public/restricted resources. Published public resources are accessible to visitors; unpublished or restricted resources are denied unless a verified entitlement is available. In this phase `user_has_entitlement()` always returns false because no entitlement store or payment workflow exists. Restricted files have no delivery route, and payment processing remains disabled.

Exam logic stays in the existing `exam_engine` modules: `models.py`, `services.py`, `views.py`, `urls.py`, `forms.py`, `admin.py`, and `tests.py`. Templates and browser assets are under `templates/exam_engine/` and `static/exam_engine/`. Do not create duplicate model or service modules; future work should extend these named boundaries unless an approved requirement demonstrates a responsibility they cannot own.

## Content editorial workflow

1. Sign in to `/admin/` with an authorized staff account.
2. Create a page in **Content pages**, enter its English or Bengali title/body, summary, and SEO fields, then save it as a draft.
3. Use **Preview page** on the saved page. The route requires staff authentication and the content view permission; it shows a draft without publishing it.
4. Add optional exam, stage, year, resource type, subject, and topic classification in the **Resource metadata** inline. Upload PDFs separately under **Resource files** and choose public or restricted visibility.
5. To publish, check **Is published** and save. A publication timestamp is set if missing. The page then appears in matching public listings and its stable URL. A complete exam resource URL needs category, stage, year, type, and page slug.
6. Edit the same page to update it and keep the slug stable after publication. To unpublish, clear **Is published** and save. Public page and file routes then return not found. Restricted PDFs have no delivery endpoint in this phase.

Public PDF display is a browser convenience; viewers can still save, print, screenshot, or copy documents. Uploaded files are stored beneath `MEDIA_ROOT`; production web-server configuration must not expose that directory directly.

## Local free study-material demo

The Free Study Materials navigation uses the existing `ExamCategory`, `Subject`, `ContentPage`, and `ResourceMetadata` records. For local navigation/rendering checks, seed clearly labelled illustrative pages with the development settings:

```powershell
$env:DJANGO_SETTINGS_MODULE = "config.settings.development"
python manage.py seed_demo_study_materials
```

The command only runs when `DEBUG=True`, creates missing rows by stable slugs, refuses conflicting records, and never deletes or silently edits existing content. It is an explicit local command and is not part of startup or deployment. It creates WBPSC Clerkship and WBCS demos with History, General Studies, Mathematics, and Geography mappings, two sample years per exam/subject pairing, and three original illustrative multiple-choice questions per paper. Demo pages are published to test public navigation and every page warns that its content is not authentic or verified official WBPSC material. No PDF is required.

Try `/free-resources/`, `/free-resources/wbpsc-clerkship/`, `/free-resources/wbpsc-clerkship/history/`, and `/free-resources/wbpsc-clerkship/history/demo-wbpsc-clerkship-history-2023-previous-question-paper/`. Existing stage/year/resource archives under `/free-resources/` remain available.

## Verification commands

```powershell
python manage.py check
python manage.py check --database default
python manage.py test content config
python manage.py test accounts access_control exam_engine content config
python manage.py makemigrations --check --dry-run
```

The account, access, content and exam journeys, permissions, publication rules, lifecycle, scoring and answer visibility are tested against PostgreSQL when PostgreSQL variables are configured in the process environment.

## OCI deployment

The approved single-host OCI pilot layout, Nginx/Gunicorn/systemd configuration, PostgreSQL migration and backup procedures, smoke checks, and rollback guide are in [deploy/README.md](deploy/README.md). The deployment guide is configuration and planning only until it is exercised on an authorized OCI tenancy. Do not claim the backup/restore process is verified until a separate-environment restoration succeeds.
