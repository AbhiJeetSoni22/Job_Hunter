"""multi user data isolation

Revision ID: 9d4e5f6a7b8c
Revises: 8c3d4e5f6a7b
Create Date: 2026-09-22 14:45:00.000000

Architecture changes:
- Creates `user_jobs` table for per-user application tracking and AI match results.
- Relocates user-specific columns (status, notes, match_score, missing_skills,
  match_summary, matched_at, resume_uploaded_at) from `jobs` to `user_jobs`.
- Adds `user_id` foreign key (CASCADE) to `resumes` and `scoring_runs`.
- Safe backfill: maps existing resume, scoring runs, and scored jobs to the owner
  verified by resume text (abhisonijeet123@gmail.com) or earliest registered user.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "9d4e5f6a7b8c"
down_revision: Union[str, None] = "8c3d4e5f6a7b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Create user_jobs table ──────────────────────────────────────────
    op.create_table(
        "user_jobs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="saved", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("match_score", sa.Integer(), nullable=True),
        sa.Column("missing_skills", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("match_summary", sa.Text(), nullable=True),
        sa.Column("matched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resume_uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "job_id", name="uq_user_jobs_user_id_job_id"),
    )
    op.create_index("idx_user_jobs_job_id", "user_jobs", ["job_id"], unique=False)
    op.create_index("idx_user_jobs_user_id", "user_jobs", ["user_id"], unique=False)
    op.create_index("idx_user_jobs_user_score", "user_jobs", ["user_id", "match_score"], unique=False)
    op.create_index("idx_user_jobs_user_status", "user_jobs", ["user_id", "status"], unique=False)

    # ── 2. Add nullable user_id to resumes ─────────────────────────────────
    op.add_column("resumes", sa.Column("user_id", sa.UUID(), nullable=True))
    op.create_foreign_key("fk_resumes_user_id_users", "resumes", "users", ["user_id"], ["id"], ondelete="CASCADE")
    op.create_index("idx_resumes_user_uploaded", "resumes", ["user_id", "uploaded_at"], unique=False)

    # ── 3. Add nullable user_id to scoring_runs ────────────────────────────
    op.add_column("scoring_runs", sa.Column("user_id", sa.UUID(), nullable=True))
    op.create_foreign_key("fk_scoring_runs_user_id_users", "scoring_runs", "users", ["user_id"], ["id"], ondelete="CASCADE")
    op.create_index("idx_scoring_runs_user_created", "scoring_runs", ["user_id", "created_at"], unique=False)

    # ── 4. Safe data backfill ──────────────────────────────────────────────
    conn = op.get_bind()

    # Determine owner user for existing single-user data
    # Priority: user matching verified resume email -> earliest registered user
    target_user_id = conn.execute(
        sa.text("SELECT id FROM users WHERE email = 'abhisonijeet123@gmail.com' LIMIT 1")
    ).scalar()

    if not target_user_id:
        target_user_id = conn.execute(
            sa.text("SELECT id FROM users ORDER BY created_at ASC LIMIT 1")
        ).scalar()

    if target_user_id:
        # Backfill existing resume and scoring runs to the owner
        conn.execute(
            sa.text("UPDATE resumes SET user_id = :uid WHERE user_id IS NULL"),
            {"uid": target_user_id},
        )
        conn.execute(
            sa.text("UPDATE scoring_runs SET user_id = :uid WHERE user_id IS NULL"),
            {"uid": target_user_id},
        )

        # Backfill user_jobs from existing jobs with non-default tracking or score data
        conn.execute(
            sa.text("""
                INSERT INTO user_jobs (
                    id, user_id, job_id, status, notes, match_score,
                    missing_skills, match_summary, matched_at,
                    resume_uploaded_at, created_at, updated_at
                )
                SELECT
                    gen_random_uuid(), :uid, id, status, notes, match_score,
                    missing_skills, match_summary, matched_at,
                    resume_uploaded_at, now(), now()
                FROM jobs
                WHERE status != 'saved' OR notes IS NOT NULL OR match_score IS NOT NULL
                ON CONFLICT (user_id, job_id) DO NOTHING
            """),
            {"uid": target_user_id},
        )
    else:
        # If no user accounts exist (e.g. fresh database), remove unassociated resumes/scoring runs
        conn.execute(sa.text("DELETE FROM resumes WHERE user_id IS NULL"))
        conn.execute(sa.text("DELETE FROM scoring_runs WHERE user_id IS NULL"))

    # ── 5. Set user_id columns to NOT NULL ─────────────────────────────────
    op.alter_column("resumes", "user_id", nullable=False)
    op.alter_column("scoring_runs", "user_id", nullable=False)

    # ── 6. Drop user-specific columns and indexes from jobs table ──────────
    op.drop_index("idx_jobs_score", table_name="jobs")
    op.drop_index("idx_jobs_status", table_name="jobs")
    op.drop_column("jobs", "status")
    op.drop_column("jobs", "notes")
    op.drop_column("jobs", "match_score")
    op.drop_column("jobs", "missing_skills")
    op.drop_column("jobs", "match_summary")
    op.drop_column("jobs", "matched_at")
    op.drop_column("jobs", "resume_uploaded_at")


def downgrade() -> None:
    # Re-add columns to jobs
    op.add_column("jobs", sa.Column("resume_uploaded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("matched_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("match_summary", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("missing_skills", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("jobs", sa.Column("match_score", sa.Integer(), nullable=True))
    op.add_column("jobs", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("status", sa.String(length=20), server_default="saved", nullable=False))
    op.create_index("idx_jobs_status", "jobs", ["status"], unique=False)
    op.create_index("idx_jobs_score", "jobs", ["match_score"], unique=False)

    # Drop user_jobs
    op.drop_index("idx_user_jobs_user_status", table_name="user_jobs")
    op.drop_index("idx_user_jobs_user_score", table_name="user_jobs")
    op.drop_index("idx_user_jobs_user_id", table_name="user_jobs")
    op.drop_index("idx_user_jobs_job_id", table_name="user_jobs")
    op.drop_table("user_jobs")

    # Drop user_id from scoring_runs
    op.drop_index("idx_scoring_runs_user_created", table_name="scoring_runs")
    op.drop_constraint("fk_scoring_runs_user_id_users", "scoring_runs", type_="foreignkey")
    op.drop_column("scoring_runs", "user_id")

    # Drop user_id from resumes
    op.drop_index("idx_resumes_user_uploaded", table_name="resumes")
    op.drop_constraint("fk_resumes_user_id_users", "resumes", type_="foreignkey")
    op.drop_column("resumes", "user_id")
