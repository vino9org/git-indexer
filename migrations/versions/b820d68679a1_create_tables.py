"""create tables

Revision ID: b820d68679a1
Revises: 
Create Date: 2023-12-11 01:48:52.104764

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b820d68679a1"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "gi_authors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=1024), nullable=False),
        sa.Column("company", sa.String(length=64), nullable=True),
        sa.Column("team", sa.String(length=64), nullable=True),
        sa.Column("author_group", sa.String(length=64), nullable=True),
        sa.Column("login_name", sa.String(length=128), nullable=True),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["gi_authors.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "gi_repositories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repo_type", sa.String(length=20), nullable=True),
        sa.Column("repo_name", sa.String(length=128), nullable=True),
        sa.Column("repo_group", sa.String(length=64), nullable=True),
        sa.Column("component", sa.String(length=64), nullable=True),
        sa.Column("clone_url", sa.String(length=256), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_indexed_at", sa.DateTime(), nullable=True),
        sa.Column("last_commit_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "gi_commits",
        sa.Column("sha", sa.String(length=40), nullable=False),
        sa.Column("message", sa.String(length=2048), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("created_at_tz", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_merge", sa.Boolean(), nullable=False),
        sa.Column("n_lines", sa.Integer(), nullable=False),
        sa.Column("n_files", sa.Integer(), nullable=False),
        sa.Column("n_insertions", sa.Integer(), nullable=False),
        sa.Column("n_deletions", sa.Integer(), nullable=False),
        sa.Column("n_lines_changed", sa.Integer(), nullable=False),
        sa.Column("n_lines_ignored", sa.Integer(), nullable=False),
        sa.Column("n_files_changed", sa.Integer(), nullable=False),
        sa.Column("n_files_ignored", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["gi_authors.id"],
        ),
        sa.PrimaryKeyConstraint("sha"),
    )
    op.create_table(
        "gi_merge_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=1024), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("source_sha", sa.String(length=256), nullable=True),
        sa.Column("source_branch", sa.String(length=256), nullable=False),
        sa.Column("target_branch", sa.String(length=256), nullable=True),
        sa.Column("merge_sha", sa.String(length=256), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("merged_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("first_comment_at", sa.DateTime(), nullable=True),
        sa.Column("is_merged", sa.Boolean(), nullable=False),
        sa.Column("merged_by_username", sa.String(length=32), nullable=True),
        sa.Column("has_tests", sa.Boolean(), nullable=True),
        sa.Column("has_test_passed", sa.Boolean(), nullable=True),
        sa.Column("repo_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["repo_id"],
            ["gi_repositories.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "gi_committed_files",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("change_type", sa.String(length=16), nullable=False),
        sa.Column("file_path", sa.String(length=256), nullable=False),
        sa.Column("file_name", sa.String(length=128), nullable=False),
        sa.Column("file_type", sa.String(length=128), nullable=False),
        sa.Column("n_lines_added", sa.Integer(), nullable=False),
        sa.Column("n_lines_deleted", sa.Integer(), nullable=False),
        sa.Column("n_lines_changed", sa.Integer(), nullable=False),
        sa.Column("n_lines_of_code", sa.Integer(), nullable=False),
        sa.Column("n_methods", sa.Integer(), nullable=False),
        sa.Column("n_methods_changed", sa.Integer(), nullable=False),
        sa.Column("is_on_exclude_list", sa.Boolean(), nullable=False),
        sa.Column("is_superfluous", sa.Boolean(), nullable=False),
        sa.Column("commit_sha", sa.String(length=40), nullable=False),
        sa.ForeignKeyConstraint(
            ["commit_sha"],
            ["gi_commits.sha"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "gi_repo_to_commits",
        sa.Column("repo_id", sa.Integer(), nullable=False),
        sa.Column("commit_id", sa.String(length=40), nullable=False),
        sa.ForeignKeyConstraint(
            ["commit_id"],
            ["gi_commits.sha"],
        ),
        sa.ForeignKeyConstraint(
            ["repo_id"],
            ["gi_repositories.id"],
        ),
        sa.PrimaryKeyConstraint("repo_id", "commit_id"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("gi_repo_to_commits")
    op.drop_table("gi_committed_files")
    op.drop_table("gi_merge_requests")
    op.drop_table("gi_commits")
    op.drop_table("gi_repositories")
    op.drop_table("gi_authors")
    # ### end Alembic commands ###
