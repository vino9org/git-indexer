import traceback
from datetime import datetime, timezone

from git.exc import GitCommandError
from loguru import logger
from psycopg import DatabaseError
from pydriller import Repository as PyDrillerRepository
from pydriller.domain.commit import Commit as PyDrillerCommit
from sqlalchemy.orm import Session

from .models import (
    Author,
    Commit,
    CommittedFile,
    Repository,
    ensure_repository,
    repo_commit_hashes,
)
from .utils import display_url, should_exclude_from_stats

GITLAB_TIMETSAMP_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

#
# notes about timezone handling (TODO: proof read)
#
#  1. For uniformity, we use timezone.utc for all datetime objects, which means some conversion is needed here
#  2. Github APIs returns native datetime object and the timezone is assumed to be in UTC
#  3. Gitlab APIs returns timetime as stringm with "Z" at the end, also in UTC
#  4. In model Repository, last_commit_at and last_indexed_at are in UTC. the commiter_date from a Git commit
#     is converted to UTC before saving to database
#


def index_commits(
    session: Session,
    clone_url: str,
    local_repo_path: str,
    repo_source: str,
    index_all: bool = False,
    timeout: int = 28800,
) -> tuple[Repository | None, int]:
    """
    this method traverses the local clone and index commits

    returns a tuple of
      repo: the Repository object in db
      n_new_commits: number of new commits indexed

    """
    n_new_commits = 0
    log_url = display_url(clone_url)

    try:
        repo = ensure_repository(session, clone_url, repo_source)
        if repo is None:
            logger.warning(f"cannot create repostitory object for {log_url}")
            return None, 0

        if repo.is_active is False:
            logger.info(f"skipping inactive repository {log_url}")
            return repo, 0

        logger.info(f"starting to index {log_url}")
        start_t = datetime.now()

        old_commits = repo_commit_hashes(repo)

        if repo.last_commit_at and not index_all:
            index_since = repo.last_commit_at
        else:
            index_since = datetime.min  # type: ignore

        for git_commit in PyDrillerRepository(
            local_repo_path,
            include_refs=True,
            include_remotes=True,
            since=index_since,
        ).traverse_commits():
            # impose some timeout to avoid spending tons of time on very large repositories
            if (datetime.now() - start_t).seconds > timeout:  # pragma: no cover
                logger.warning(f"### indexing not done after {timeout} seconds, aborting {log_url}")
                break

            if git_commit.hash not in old_commits:
                # check if the same repo is already linked to another repo
                commit = session.query(Commit).filter_by(sha=git_commit.hash).first()
                if commit is None:
                    commit = _new_commit_(session, git_commit)

                commit.repos.append(repo)
                session.add(commit)
                session.commit()

                if repo.last_commit_at is None or commit.created_at > repo.last_commit_at:  # type: ignore
                    repo.last_commit_at = commit.created_at

                n_new_commits += 1

        if n_new_commits > 0:
            logger.info(f"indexed {n_new_commits:5,} new commits in the repository")

        repo.last_indexed_at = datetime.utcnow()  # type: ignore
        session.add(repo)
        session.commit()

        return repo, n_new_commits

    except GitCommandError as e:
        logger.warning(f"{e._cmdline} returned {e.stderr} for {log_url}")
    except DatabaseError as e:
        exc = traceback.format_exc()
        logger.warning(f"DatabaseError indexing repository {log_url} => {str(e)}\n{exc}")
    except Exception as e:  # pragma: no cover
        exc = traceback.format_exc()
        logger.warning(f"Exception indexing repository {log_url} => {str(e)}\n{exc}")

    return None, 0


def _new_commit_(session: Session, git_commit: PyDrillerCommit) -> Commit:
    author_email = git_commit.committer.email.lower()
    author = session.query(Author).filter_by(email=author_email).first()
    if author is None:
        author = Author(name=git_commit.committer.name, email=author_email)
        session.add(author)
        session.commit()

    commit = Commit(
        sha=git_commit.hash,
        message=git_commit.msg[:2048],  # some commits has super long message, e.g. squash merge
        author=author,
        is_merge=git_commit.merge,
        n_lines=git_commit.lines,
        n_files=git_commit.files,
        n_insertions=git_commit.insertions,
        n_deletions=git_commit.deletions,
        created_at_tz=git_commit.committer_date,
        created_at=git_commit.committer_date.astimezone(timezone.utc).replace(tzinfo=None),
    )

    n_lines_changed, n_lines_ignored, n_files_changed, n_files_ignored = 0, 0, 0, 0

    for mod in git_commit.modified_files:
        file_path = mod.new_path or mod.old_path
        is_excluded = should_exclude_from_stats(file_path)

        new_file = CommittedFile(
            commit_sha=git_commit.hash,
            change_type=str(mod.change_type).split(".")[1],  # enum ModificationType.ADD => "ADD"
            file_path=file_path,
            file_name=mod.filename,
            n_lines_added=mod.added_lines,
            n_lines_deleted=mod.deleted_lines,
            n_lines_changed=mod.added_lines + mod.deleted_lines,
            n_lines_of_code=mod.nloc if mod.nloc else 0,
            n_methods=len(mod.methods),
            n_methods_changed=len(mod.changed_methods),
            is_on_exclude_list=is_excluded,
            is_superfluous=is_excluded,
            commit=commit,
        )
        session.add(new_file)

        if is_excluded:
            n_files_ignored += 1
            n_lines_ignored += new_file.n_lines_changed
        else:
            n_files_changed += 1
            n_lines_changed += new_file.n_lines_changed

    commit.n_lines_changed = n_lines_changed
    commit.n_lines_ignored = n_lines_ignored
    commit.n_files_changed = n_files_changed
    commit.n_files_ignored = n_files_ignored
    session.add(commit)

    return commit
