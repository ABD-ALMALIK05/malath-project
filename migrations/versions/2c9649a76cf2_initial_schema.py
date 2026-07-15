"""Create the initial Malath schema without replacing existing tables.

Revision ID: 2c9649a76cf2
Revises:
Create Date: 2026-07-15 22:52:23.808723

"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "2c9649a76cf2"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    existing_tables = set(sa.inspect(op.get_bind()).get_table_names())

    if "user" not in existing_tables:
        op.create_table(
            "user",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("full_name", sa.String(length=150), nullable=False),
            sa.Column("username", sa.String(length=80), nullable=False),
            sa.Column("email", sa.String(length=120), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column("pin_hash", sa.String(length=255), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("email"),
            sa.UniqueConstraint("username"),
        )

    if "document" not in existing_tables:
        op.create_table(
            "document",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("category", sa.String(length=50), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("file_url", sa.String(length=500), nullable=False),
            sa.Column("stored_filename", sa.String(length=255), nullable=False),
            sa.Column("original_filename", sa.String(length=255), nullable=False),
            sa.Column("file_type", sa.String(length=20), nullable=False),
            sa.Column("file_size", sa.Integer(), nullable=False),
            sa.Column("upload_date", sa.DateTime(), nullable=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade():
    raise RuntimeError(
        "Downgrading the initial schema is disabled because it may contain existing user data."
    )
