# Security Policy

## Supported Version

Security fixes are intended for the current `0.2.x` release line. Older repository snapshots may
not include the latest hardening work.

## Reporting A Vulnerability

Please report suspected vulnerabilities privately. Use the repository's private vulnerability
reporting feature when it is available. If that feature is unavailable, contact the maintainer
through an existing non-public project channel and ask for a secure reporting path.

Do not open a public issue containing exploit steps, credentials, personal documents, session
tokens, private URLs, or other sensitive evidence. A useful report includes the affected version,
the relevant route or component, reproducible steps using non-sensitive test data, impact, and any
suggested mitigation. Allow time for investigation before public disclosure.

## Sensitive Data

- Never commit `.env` files, secret keys, AWS credentials, session tokens, SQLite databases,
  uploaded documents, presigned URLs, or production logs.
- Use synthetic documents and accounts when reproducing an issue.
- Revoke and rotate any credential that may have been exposed.
- Keep S3 buckets private and grant only the object permissions the application requires.
- Back up important databases and stored files before applying migrations or operational changes.

## Security Scope

Malath includes password hashing, CSRF protection, temporary PIN verification, ownership checks,
private file access, configurable secure cookies, basic in-memory rate limits, and generic error
handling. These controls reduce common risks but do not constitute a security certification.

Malath is an educational and practical project, not a certified document custody or legal
archiving service. The PIN gate does not encrypt documents, file validation is not malware
scanning, and secure deployment still requires HTTPS, protected infrastructure, restricted
database and storage access, monitoring, backups, dependency updates, and environment-specific
review.
