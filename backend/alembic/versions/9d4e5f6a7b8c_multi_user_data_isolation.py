"""multi user data isolation

Revision ID: 9d4e5f6a7b8c
Revises: 8c3d4e5f6a7b
Create Date: 2026-09-22 14:45:00.000000

Architecture changes:
- Creates `user_jobs` table for per-user application tracking and AI match results.
- Relocates user-specific columns (status, notes, match_score, missing_skills,
  match_summary, matched_at, resume_uploaded_at) from `jobs` to `user_jobs`.
- Adds `user_id` foreign key (CASCADE) to `resumes` and `scoring_runs`.
- Safe deterministic backfill: on single-user installations, maps existing resume,
  scoring runs, and all legacy jobs to the single registered user account. Fails
  clearly with an actionable error if ownership is ambiguous or missing, avoiding
  silent data deletion or arbitrary assignment.
- Reversible downgrade restoring job states from user_jobs.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9d4e5f6a7b8c"
down_revision: str | None = "8c3d4e5f6a7b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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

    # Inspect existing users
    users = conn.execute(sa.text("SELECT id FROM users ORDER BY created_at ASC")).fetchall()
    user_count = len(users)

    # Inspect existing unassigned records in resumes and scoring_runs
    unassigned_resumes = conn.execute(
        sa.text("SELECT count(*) FROM resumes WHERE user_id IS NULL")
    ).scalar() or 0
    unassigned_scoring_runs = conn.execute(
        sa.text("SELECT count(*) FROM scoring_runs WHERE user_id IS NULL")
    ).scalar() or 0

    # Inspect whether legacy user-specific job state exists in the jobs table before dropping columns.
    # A job is considered to contain meaningful user-specific state if:
    # - status is non-default (not 'saved', e.g. 'applied', 'interview', 'rejected', 'archived')
    # - OR notes is not null
    # - OR match_score is not null
    # - OR missing_skills is not null
    # - OR match_summary is not null
    # - OR matched_at is not null
    # - OR resume_uploaded_at is not null
    meaningful_legacy_jobs = conn.execute(
        sa.text("""
            SELECT count(*) FROM jobs
            WHERE (status IS NOT NULL AND status != 'saved')
               OR notes IS NOT NULL
               OR match_score IS NOT NULL
               OR missing_skills IS NOT NULL
               OR match_summary IS NOT NULL
               OR matched_at IS NOT NULL
               OR resume_uploaded_at IS NOT NULL
        """)
    ).scalar() or 0

    if user_count == 1:
        # Case 1: Standard upgrade from single-user to multi-user: exactly one user account exists.
        # Treat that single user as the legacy owner.
        target_user_id = users[0][0]

        conn.execute(
            sa.text("UPDATE resumes SET user_id = :uid WHERE user_id IS NULL"),
            {"uid": target_user_id},
        )
        conn.execute(
            sa.text("UPDATE scoring_runs SET user_id = :uid WHERE user_id IS NULL"),
            {"uid": target_user_id},
        )

        # Backfill all existing jobs into user_jobs to preserve the legacy user's saved status,
        # notes, and match evaluations. In the previous single-user architecture, all jobs in the
        # database represented that single user's job board (including status='saved' jobs).
        conn.execute(
            sa.text("""
                INSERT INTO user_jobs (
                    id, user_id, job_id, status, notes, match_score,
                    missing_skills, match_summary, matched_at,
                    resume_uploaded_at, created_at, updated_at
                )
                SELECT
                    gen_random_uuid(), :uid, id,
                    COALESCE(status, 'saved'),
                    notes, match_score, missing_skills, match_summary, matched_at,
                    resume_uploaded_at,
                    COALESCE(created_at, now()),
                    COALESCE(updated_at, now())
                FROM jobs
                ON CONFLICT (user_id, job_id) DO NOTHING
            """),
            {"uid": target_user_id},
        )

    elif user_count == 0:
        # Case 2: Zero users exist.
        # If any user-owned records (resumes, scoring runs) or meaningful user-specific job states exist,
        # we cannot determine ownership without a user account. Refuse to discard or delete data.
        has_unassigned_data = (
            unassigned_resumes > 0
            or unassigned_scoring_runs > 0
            or meaningful_legacy_jobs > 0
        )
        if has_unassigned_data:
            raise RuntimeError(
                f"Migration aborted: Found existing legacy data requiring ownership ("
                f"{unassigned_resumes} unassigned resumes, "
                f"{unassigned_scoring_runs} unassigned scoring runs, "
                f"{meaningful_legacy_jobs} jobs with user-specific state) "
                "but no user accounts exist in the 'users' table. "
                "Cannot determine data ownership without a user account, and refusing to silently delete or discard data. "
                "Please register the owner user account first or assign user_id manually before running this migration."
            )
        # Genuinely fresh/empty database or only raw scraped jobs (status='saved', no user state).
        # Safe to proceed without populating user_jobs.

    else:
        # Case 3: Multiple users already exist.
        # If unassigned resumes, scoring runs, or jobs with user-specific state exist,
        # automatic backfill cannot determine ownership among multiple users.
        has_unassigned_data = (
            unassigned_resumes > 0
            or unassigned_scoring_runs > 0
            or meaningful_legacy_jobs > 0
        )
        if has_unassigned_data:
            raise RuntimeError(
                f"Migration aborted: Found {user_count} users in the database and unassigned legacy data ("
                f"{unassigned_resumes} unassigned resumes, "
                f"{unassigned_scoring_runs} unassigned scoring runs, "
                f"{meaningful_legacy_jobs} jobs with user-specific state). "
                "Automatic backfill cannot safely determine data ownership among multiple users. "
                "Please manually assign user_id to existing records or resolve ownership before running this migration."
            )
        # If there is no meaningful legacy user-specific job state (and no unassigned resumes/scoring runs),
        # migration may proceed because there is nothing to migrate into user_jobs.

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
    # 1. Re-add columns to jobs
    op.add_column("jobs", sa.Column("resume_uploaded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("matched_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("match_summary", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("missing_skills", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("jobs", sa.Column("match_score", sa.Integer(), nullable=True))
    op.add_column("jobs", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("status", sa.String(length=20), server_default="saved", nullable=False))
    op.create_index("idx_jobs_status", "jobs", ["status"], unique=False)
    op.create_index("idx_jobs_score", "jobs", ["match_score"], unique=False)

    # 2. Reversibly restore user_jobs data into jobs where practical
    conn = op.get_bind()
    conn.execute(
        sa.text("""
            UPDATE jobs j
            SET
                status = uj.status,
                notes = uj.notes,
                match_score = uj.match_score,
                missing_skills = uj.missing_skills,
                match_summary = uj.match_summary,
                matched_at = uj.matched_at,
                resume_uploaded_at = uj.resume_uploaded_at
            FROM user_jobs uj
            WHERE uj.job_id = j.id
        """)
    )

    # 3. Drop user_jobs
    op.drop_index("idx_user_jobs_user_status", table_name="user_jobs")
    op.drop_index("idx_user_jobs_user_score", table_name="user_jobs")
    op.drop_index("idx_user_jobs_user_id", table_name="user_jobs")
    op.drop_index("idx_user_jobs_job_id", table_name="user_jobs")
    op.drop_table("user_jobs")

    # 4. Drop user_id from scoring_runs
    op.drop_index("idx_scoring_runs_user_created", table_name="scoring_runs")
    op.drop_constraint("fk_scoring_runs_user_id_users", "scoring_runs", type_="foreignkey")
    op.drop_column("scoring_runs", "user_id")

    # 5. Drop user_id from resumes
    op.drop_index("idx_resumes_user_uploaded", table_name="resumes")
    op.drop_constraint("fk_resumes_user_id_users", "resumes", type_="foreignkey")
    op.drop_column("resumes", "user_id")
