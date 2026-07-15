# Database migrations

Malath uses Flask-Migrate and Alembic to apply schema changes. Migrations are never run when
the application is imported.

After installing the runtime dependencies and configuring `DATABASE_URL`, apply all pending
migrations with:

```text
flask --app wsgi db upgrade
```

The initial migration creates missing tables on a fresh database and leaves matching tables in
an existing SQLite database intact. Back up important data before applying future migrations.
The initial baseline cannot be downgraded automatically because its tables may contain data that
predates Alembic.
