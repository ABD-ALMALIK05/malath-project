# Changelog

Notable changes to Malath are documented here.

## [0.2.0] - 2026-07-15

### Added

- Modular Flask application factory and public, authentication, and document blueprints
- Private local storage backend and optional private S3 backend
- PDF, PNG, and JPEG content validation
- CSRF protection, expiring PIN verification, rate limits, and security headers
- Bilingual operational error pages and a versioned health endpoint
- Flask-Migrate and Alembic database migration support
- Responsive and accessible bilingual document workflows
- Deterministic pytest coverage across authentication, security, documents, storage, i18n,
  migrations, errors, and health behavior
- GitHub Actions quality checks and weekly Dependabot configuration

### Changed

- Environment-backed configuration replaces hardcoded application and AWS settings
- Document downloads now pass through backend-neutral, authorization-aware storage services
- Logout and PIN-clear operations now require protected POST requests
- Project metadata, dependency separation, supported Python versions, linting, formatting, and
  coverage configuration are standardized

### Security

- Added password complexity checks, safe redirect validation, ownership-filtered document queries,
  secure session defaults, generic storage failures, and reduced sensitive logging
- Replaced permanent PIN session state with a configurable time-limited verification window

### Compatibility

- Existing `file_url` and `stored_filename` columns remain available for legacy database records
- `python app.py` remains a supported local development entry point
