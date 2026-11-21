"""Initial FastAPI schema; legacy Django tables are imported separately."""
from alembic import op
import sqlalchemy as sa

revision = "0001_fastapi"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(150), nullable=False, unique=True),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("password_hash", sa.String(512), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("auth_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("csrf_token", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False))
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])
    op.create_table("documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("storage_path", sa.String(512), nullable=False),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("extension", sa.String(8), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("user_documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("prompt_version", sa.String(30), nullable=False),
        sa.Column("attempt_id", sa.String(36), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "sha256", name="unique_user_document_hash"))
    op.create_index("ix_user_documents_user_id", "user_documents", ["user_id"])


def downgrade():
    op.drop_table("user_documents")
    op.drop_table("documents")
    op.drop_table("auth_sessions")
    op.drop_table("users")
