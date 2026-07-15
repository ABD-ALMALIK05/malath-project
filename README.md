# Malath | ملاذ

Malath is a bilingual Arabic and English Flask application for organizing personal documents in
one private account. It combines account authentication, a temporary six-digit PIN gate,
document categories, dashboard statistics, and controlled file operations in a responsive
interface.

This project addresses a practical problem: important civil, medical, property, and personal
documents are often scattered across devices and folders. Malath provides a consistent archive
and retrieval workflow while keeping access checks in the application.

Malath is an educational and practical software project. It is not a certified document custody,
records-compliance, legal archiving, or disaster-recovery service.

## Capabilities

- Bilingual Arabic and English interface with right-to-left Arabic layouts
- Account registration and password-based authentication
- Temporary PIN-protected document area
- Dashboard statistics and recent-document summaries
- Government, medical, property, and personal categories
- PDF, PNG, and JPEG upload validation
- Authenticated upload, download, edit, filter, and delete workflows
- Private local development storage
- Optional private Amazon S3 storage with short-lived download links
- Responsive, keyboard-accessible interface
- Automated pytest suite with an 80% coverage gate
- GitHub Actions quality checks and Dependabot updates
- Operational health endpoint at `GET /health`

## Technology

- Python 3.11 or 3.12
- Flask and Jinja
- Bootstrap and project CSS
- SQLAlchemy and Flask-SQLAlchemy
- Flask-Login
- Flask-Migrate and Alembic
- SQLite by default
- Optional Amazon S3 through boto3
- Pillow for image verification
- pytest, pytest-cov, and Ruff
- GitHub Actions

## Architecture

The application uses a Flask application factory. Extensions are initialized without binding
them at import time, and blueprints separate public pages, authentication, and document
workflows. Storage and file validation live behind service modules, so local and S3 storage use
the same document routes. Alembic owns database schema upgrades; migrations do not run when the
application is imported.

```text
malath-project/
├── malath/
│   ├── auth/                 # Registration, login, logout, and PIN routes
│   ├── documents/            # Document archive routes
│   ├── main/                 # Landing page, dashboard, and health route
│   ├── services/             # Storage backends and file validation
│   ├── static/               # CSS and existing visual assets
│   ├── templates/            # English/Arabic-aware Jinja templates
│   ├── __init__.py           # Application factory
│   ├── config.py             # Environment-backed configuration
│   ├── errors.py             # Bilingual HTTP error handling
│   ├── extensions.py         # Flask extension instances
│   ├── i18n.py               # Translations and localization helpers
│   ├── models.py             # User and Document models
│   ├── security.py           # CSRF, rate limit, redirect, and PIN helpers
│   └── version.py            # Application version source
├── migrations/              # Alembic migration environment and revisions
├── tests/                   # Isolated pytest suite
├── app.py                   # Compatibility development entry point
├── wsgi.py                  # Flask CLI and WSGI entry point
├── requirements.txt         # Runtime dependencies
└── requirements-dev.txt     # Test and quality dependencies
```

## Windows Setup

Use Python 3.11 or 3.12 in PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt
Copy-Item .env.example .env
flask --app wsgi db upgrade
flask --app wsgi run
```

Open `http://127.0.0.1:5000`. `python app.py` remains available as a compatibility development
command after the database migration has been applied.

## Linux And macOS Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
flask --app wsgi db upgrade
flask --app wsgi run
```

## Configuration

Copy `.env.example` to `.env` for local use. The `.env` file is ignored by Git. Replace examples
with values appropriate for the environment and never commit credentials.

| Variable | Requirement | Purpose | Safe example |
| --- | --- | --- | --- |
| `SECRET_KEY` | Required in production | Signs Flask sessions and CSRF state | `replace-with-a-random-local-value` |
| `DATABASE_URL` | Optional | SQLAlchemy database connection | `sqlite:///instance/malath.db` |
| `STORAGE_BACKEND` | Optional | Selects `local` or `s3` storage | `local` |
| `LOCAL_STORAGE_PATH` | Required for local mode | Private upload directory outside static assets | `instance/uploads` |
| `AWS_ACCESS_KEY_ID` | Optional with AWS role/profile | AWS credential-chain access key | Leave blank for an IAM role |
| `AWS_SECRET_ACCESS_KEY` | Optional with AWS role/profile | AWS credential-chain secret | Leave blank for an IAM role |
| `AWS_S3_BUCKET` | Required for S3 mode | Private S3 bucket name | `my-private-malath-bucket` |
| `AWS_REGION` | Required for S3 mode | S3 bucket region | `eu-north-1` |
| `SESSION_COOKIE_SECURE` | Recommended outside local HTTP | Sends the session cookie over HTTPS only | `true` |
| `PIN_VERIFICATION_MINUTES` | Optional | Duration of temporary document-area access | `15` |
| `MAX_CONTENT_LENGTH` | Optional | Maximum request size in bytes | `5242880` |
| `S3_PRESIGNED_EXPIRES_SECONDS` | Optional | S3 download-link lifetime | `300` |
| `LOG_LEVEL` | Optional | Application log threshold | `INFO` |

Production mode must provide `SECRET_KEY`; startup fails clearly when it is absent. Debug mode is
disabled unless explicitly configured for local development.

## Local Storage

Local storage is the default. Files are saved below `LOCAL_STORAGE_PATH`, outside the public
static directory, under generated storage keys. Original filenames are retained only as download
metadata. File downloads pass through an authenticated, PIN-protected route and document
ownership is checked before the file is served.

The upload directory and SQLite databases are ignored by Git. Back them up separately when the
data matters.

## Amazon S3

Set `STORAGE_BACKEND=s3`, `AWS_S3_BUCKET`, and `AWS_REGION`. The bucket is expected to block public
access. Malath uses the normal AWS credential chain, so local profiles, environment credentials,
container credentials, and IAM roles can be used without embedding keys in source code.

At a high level, the application identity needs object permissions for upload, download lookup,
and deletion within its configured object prefix, such as `s3:PutObject`, `s3:GetObject`, and
`s3:DeleteObject`. Apply least privilege to the actual bucket and prefix. Downloads use
short-lived presigned URLs; the application does not create permanent public object URLs.

Storage compatibility details are recorded in
[`docs/storage-compatibility.md`](docs/storage-compatibility.md).

## Database Migrations

Apply pending migrations after configuring `DATABASE_URL`:

```text
flask --app wsgi db upgrade
```

Create and review future model migrations with:

```text
flask --app wsgi db migrate -m "describe the schema change"
flask --app wsgi db upgrade
```

The initial migration preserves matching tables in an existing SQLite database. Back up important
data before any schema operation. See
[`docs/database-migrations.md`](docs/database-migrations.md) for baseline behavior.

## Quality Commands

```text
ruff check .
ruff format --check .
python -m compileall malath app.py wsgi.py
pytest
pytest --cov=malath --cov-report=term-missing --cov-fail-under=80
```

Tests use temporary SQLite databases and local storage. They do not require internet access or
connect to AWS. Coverage files, test databases, and test output are local or CI artifacts and are
not committed.

## Security Design

- Passwords and PINs are stored as Werkzeug password hashes, not plaintext.
- State-changing requests require a session-bound CSRF token.
- Passwords require at least eight characters, one letter, and one number.
- Login, registration, and PIN attempts have basic rate limits.
- PIN verification expires after a configurable interval and is cleared on logout.
- Redirect targets are restricted to the current host.
- Document queries include the authenticated owner ID.
- Local files are served only after authentication, PIN verification, and ownership checks.
- S3 objects remain private and downloads use expiring presigned URLs.
- Session cookies use `HttpOnly` and `SameSite=Lax`; secure transport can be enforced per
  environment.
- Common browser security headers and bilingual error responses are configured.
- Logs avoid passwords, PINs, CSRF tokens, document contents, and presigned URLs.

The PIN is an additional application access gate; it does not encrypt stored documents. Malath
does not claim end-to-end encryption, certified custody, or protection against every threat.

## Accessibility And Languages

English pages use `lang="en"` and left-to-right direction. Arabic pages use `lang="ar"` and
right-to-left direction. Navigation retains the selected language through forms and errors. The
templates include a skip link, main landmark, associated labels and validation messages,
keyboard focus styles, accessible alerts, responsive tables, and reduced-motion support.

## Current Limitations

- SQLite and local storage are suited to development or small single-instance use.
- Rate-limit state is held in process memory and is not shared across workers or hosts.
- There is no email verification, account recovery, external identity provider, or full MFA.
- Uploaded files are signature-checked but are not scanned by an antivirus or content-disarm
  service.
- Files are not encrypted by a separate application-managed key layer.
- Backup, retention, legal-hold, audit export, and disaster-recovery policies are not automated.
- S3 behavior depends on external AWS configuration and permissions.

## Future Improvements

- Replace in-memory throttling with a shared store for multi-worker deployments.
- Add verified account recovery and optional standards-based multi-factor authentication.
- Add malware scanning and configurable retention workflows.
- Add database indexes and pagination for larger archives.
- Add centralized audit events that avoid sensitive document content.
- Exercise S3 integration against a dedicated non-production test environment.
- Add deployment-specific backup, monitoring, and recovery procedures.

## Field Training Context

Malath is a practical full-stack web development project demonstrating requirements
implementation, Flask backend development, relational data modeling, authentication and
authorization, secure file handling, cloud storage integration, automated testing, continuous
integration, accessibility, bilingual interface work, and technical documentation.

Release history is available in [`CHANGELOG.md`](CHANGELOG.md). Security reporting guidance is
available in [`SECURITY.md`](SECURITY.md).
