import os
import re
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table
from sqlalchemy.orm import (
    Mapped,
    Session,
    declarative_base,
    mapped_column,
    relationship,
)

Base = declarative_base()


repo_to_commit_table = Table(
    "gi_repo_to_commits",
    Base.metadata,
    Column("repo_id", ForeignKey("gi_repositories.id"), primary_key=True),
    Column("commit_id", ForeignKey("gi_commits.sha"), primary_key=True),
)


@dataclass
class Author(Base):
    __tablename__ = "gi_authors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # noqa: A003, VNE003
    name: Mapped[str] = mapped_column(String(128))
    email: Mapped[str] = mapped_column(String(1024), unique=True)
    company: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    team: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    author_group: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    login_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    parent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("gi_authors.id"))
    parent: Mapped[Optional["Author"]] = relationship("Author", remote_side=[id], backref="aliases")

    commits: Mapped[list["Commit"]] = relationship("Commit", back_populates="author")

    def __str__(self):
        expr = f"Author(id={self.id}, email={self.email}, real_email={self.real_email})"
        if self.parent_id:
            expr += f" parent -> {self.parent.id},{self.parent.name},{self.parent.email}"
        return expr


@dataclass
class Repository(Base):
    __tablename__ = "gi_repositories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # noqa: A003, VNE003
    repo_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    repo_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    repo_group: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    component: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    clone_url: Mapped[str] = mapped_column(String(256))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_indexed_at: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)
    last_commit_at: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)

    commits: Mapped[list["Commit"]] = relationship(secondary=repo_to_commit_table, back_populates="repos")

    merge_requests: Mapped[list["MergeRequest"]] = relationship("MergeRequest", back_populates="repo")

    @property
    def browse_url(self) -> str:
        url = self.clone_url

        if self.repo_type == "local":
            url = f"http://localhost:9000/gitweb{url}"
        elif self.repo_type == "github":
            if self.clone_url.startswith("git@"):
                url = url.replace("git@github.com:", "https://github.com/")
        elif self.repo_type == "gitlab":
            if url.startswith("git@"):
                url = url.replace("git@gitlab.com:", "https://gitlab.com")
            elif url.startswith("git+ssh://git@gitlab.com/"):
                url = url.replace("git+ssh://git@", "https://")
        else:
            url = "https://invalid.url"

        return re.sub(r"\.git$", "", url)

    @property
    def url_for_commit(self) -> str:
        if self.repo_type is None:
            return ""
        elif self.repo_type == "github":
            return f"{self.browse_url}/commit"
        elif self.repo_type.startswith("gitlab"):
            return f"{self.browse_url}/-/commit"
        else:
            return ""

    def __str__(self) -> str:
        return f"Repository(id={self.id}, url={self.clone_url})"


@dataclass
class Commit(Base):
    __tablename__ = "gi_commits"

    sha: Mapped[str] = mapped_column(String(40), primary_key=True)
    message: Mapped[str] = mapped_column(String(2048), default="")
    created_at: Mapped[DateTime] = mapped_column(DateTime)
    created_at_tz: Mapped[DateTime] = mapped_column(DateTime(timezone=True))
    is_merge: Mapped[bool] = mapped_column(Boolean, default=False)
    n_lines: Mapped[int] = mapped_column(Integer, default=0)
    n_files: Mapped[int] = mapped_column(Integer, default=0)
    n_insertions: Mapped[int] = mapped_column(Integer, default=0)
    n_deletions: Mapped[int] = mapped_column(Integer, default=0)
    n_lines_changed: Mapped[int] = mapped_column(Integer, default=0)
    n_lines_ignored: Mapped[int] = mapped_column(Integer, default=0)
    n_files_changed: Mapped[int] = mapped_column(Integer, default=0)
    n_files_ignored: Mapped[int] = mapped_column(Integer, default=0)

    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("gi_authors.id"))
    author: Mapped[Author] = relationship("Author", back_populates="commits")

    repos: Mapped[list["Repository"]] = relationship(secondary=repo_to_commit_table, back_populates="commits")

    files: Mapped[list["CommittedFile"]] = relationship("CommittedFile", back_populates="commit")

    def __str__(self) -> str:
        return f"Commit(id={self.sha})"


@dataclass
class CommittedFile(Base):
    __tablename__ = "gi_committed_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # noqa: A003, VNE003
    change_type: Mapped[str] = mapped_column(String(16), default="UNKNOWN")
    file_path: Mapped[str] = mapped_column(String(256))
    file_name: Mapped[str] = mapped_column(String(128))
    file_type: Mapped[str] = mapped_column(String(128))
    n_lines_added: Mapped[int] = mapped_column(Integer, default=0)
    n_lines_deleted: Mapped[int] = mapped_column(Integer, default=0)
    n_lines_changed: Mapped[int] = mapped_column(Integer, default=0)
    n_lines_of_code: Mapped[int] = mapped_column(Integer, default=0)
    n_methods: Mapped[int] = mapped_column(Integer, default=0)
    n_methods_changed: Mapped[int] = mapped_column(Integer, default=0)
    is_on_exclude_list: Mapped[bool] = mapped_column(Boolean, default=False)
    is_superfluous: Mapped[bool] = mapped_column(Boolean, default=False)

    commit_sha: Mapped[str] = mapped_column(String(40), ForeignKey("gi_commits.sha"))
    commit: Mapped[Commit] = relationship("Commit", back_populates="files")

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        if not self.id:
            main, ext = os.path.splitext(self.file_path)
            if main.startswith("."):
                self.file_type = "hidden"
            elif ext != "":
                self.file_type = ext[1:].lower()
            else:
                self.file_type = "generic"

    def __str__(self) -> str:
        return f"CommittedFile(id={self.id}, part of Commit(sha={self.commit_sha}))"


@dataclass
class MergeRequest(Base):
    __tablename__ = "gi_merge_requests"

    id = Column(Integer, primary_key=True)  # noqa: A003, VNE003
    request_id: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(1024))
    state: Mapped[str] = mapped_column(String(32))
    source_sha: Mapped[str] = mapped_column(String(256), nullable=True)
    source_branch: Mapped[str] = mapped_column(String(256), default="")
    target_branch: Mapped[str] = mapped_column(String(256), nullable=True)
    merge_sha: Mapped[str] = mapped_column(String(256), nullable=True, default="")
    created_at: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)
    merged_at: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)
    first_comment_at: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)
    is_merged: Mapped[bool] = mapped_column(Boolean, default=False)
    merged_by_username: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    has_tests: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    has_test_passed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Relationship to Repository
    repo_id: Mapped[int] = mapped_column(Integer, ForeignKey("gi_repositories.id"))
    repo: Mapped[Repository] = relationship("Repository", back_populates="merge_requests")


def ensure_repository(session: Session, clone_url: str, repo_type: str) -> Repository:
    repo = session.query(Repository).filter_by(clone_url=clone_url, repo_type=repo_type).first()
    if repo is None:
        repo_name = clone_url.split("/")[-1].replace(".git", "")
        repo = Repository(clone_url=clone_url, repo_type=repo_type, repo_name=repo_name)
        session.add(repo)
        session.commit()
    return repo


def repo_commit_hashes(repo: Repository) -> list[str]:
    return [c.sha for c in repo.commits]
