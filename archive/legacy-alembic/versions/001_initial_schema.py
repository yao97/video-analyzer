"""initial schema

Revision ID: 001
Create Date: 2026-07-28
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================
    # jobs: task table — replaces in-memory dict
    # ============================================================
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("progress", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("video_filename", sa.String(255), nullable=True),
        sa.Column("video_duration", sa.Float, nullable=True),
        sa.Column("storage_key", sa.String(512), nullable=True),
        sa.Column("result", postgresql.JSONB, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("error_traceback", sa.Text, nullable=True),
        sa.Column("parent_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["parent_job_id"], ["jobs.id"], ondelete="SET NULL"),
    )

    op.create_index("idx_jobs_status", "jobs", ["status"],
                    postgresql_where=sa.text("status IN ('pending', 'processing')"))
    op.create_index("idx_jobs_created_at", "jobs", [sa.text("created_at DESC")])
    op.create_index("idx_jobs_parent", "jobs", ["parent_job_id"])
    op.create_index("idx_jobs_created_by", "jobs", ["created_by"])
    op.create_index("idx_jobs_result_gin", "jobs", ["result"],
                    postgresql_using="gin")

    # Auto-update updated_at trigger
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_jobs_updated
            BEFORE UPDATE ON jobs
            FOR EACH ROW EXECUTE FUNCTION update_updated_at();
    """)

    # ============================================================
    # transcripts: transcription results
    # ============================================================
    op.create_table(
        "transcripts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("video_filename", sa.String(255), nullable=True),
        sa.Column("language", sa.String(10), nullable=True),
        sa.Column("duration", sa.Float, nullable=True),
        sa.Column("segments", postgresql.JSONB, nullable=True),
        sa.Column("full_text", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
    )

    op.create_index("idx_transcripts_job", "transcripts", ["job_id"])
    op.create_index("idx_transcripts_text", "transcripts",
                    [sa.text("to_tsvector('simple', full_text)")],
                    postgresql_using="gin")

    # ============================================================
    # analysis_results: LLM analysis results
    # ============================================================
    op.create_table(
        "analysis_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transcript_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("analysis_type", sa.String(50), nullable=False),
        sa.Column("model_used", sa.String(100), nullable=True),
        sa.Column("result", postgresql.JSONB, nullable=True),
        sa.Column("tokens_used", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["transcript_id"], ["transcripts.id"], ondelete="SET NULL"),
    )

    op.create_index("idx_analysis_job", "analysis_results", ["job_id"])
    op.create_index("idx_analysis_type", "analysis_results", ["analysis_type"])

    # ============================================================
    # api_keys: server-side API key management
    # ============================================================
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("key_prefix", sa.String(20), nullable=False),
        sa.Column("key_encrypted", sa.LargeBinary, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("daily_quota", sa.Integer, nullable=False, server_default="100"),
        sa.Column("used_today", sa.Integer, nullable=False, server_default="0"),
        sa.Column("quota_reset_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )

    op.create_index("idx_apikeys_active", "api_keys", ["is_active"],
                    postgresql_where=sa.text("is_active = true"))

    # Apply updated_at trigger to api_keys as well
    op.execute("""
        CREATE TRIGGER trg_apikeys_updated
            BEFORE UPDATE ON api_keys
            FOR EACH ROW EXECUTE FUNCTION update_updated_at();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_apikeys_updated ON api_keys")
    op.execute("DROP TRIGGER IF EXISTS trg_jobs_updated ON jobs")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at()")

    op.drop_table("api_keys")
    op.drop_table("analysis_results")
    op.drop_table("transcripts")
    op.drop_table("jobs")
