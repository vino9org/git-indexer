import traceback

from git import GitCommandError
from github import Repository as github_repo
from gitlab.v4.objects import projects as gl_projects
from loguru import logger
from psycopg import DatabaseError
from sqlalchemy.orm import Session

from git_indexer.models import MergeRequest, ensure_repository
from git_indexer.utils import display_url, gitlab_ts_to_datetime


def index_github_pull_requests(session: Session, git_repo: github_repo.Repository) -> int:
    n_requests = 0
    log_url = display_url(git_repo.clone_url)

    try:
        repo = ensure_repository(session, git_repo.clone_url, "github")
        if repo is None:
            logger.info(f"### cannot create repostitory object for {log_url}")
            return 0

        if repo.is_active is False:
            logger.info(f"### skipping inactive repository {log_url}")
            return 0

        logger.info(f"starting to index merge requests for {log_url}")

        pull_requests = git_repo.get_pulls(state="closed")
        for pr in pull_requests:
            pr_id = str(pr.number)
            db_obj = session.query(MergeRequest).filter_by(request_id=pr_id, repo=repo).first()
            if db_obj is not None:
                # merge request already indexed
                continue

            # TODO: pr.created_at is a naive datetime object, timezone is assumed to be UTC
            request = MergeRequest(
                repo=repo,
                request_id=pr_id,
                title=pr.title,
                state=pr.state,
                source_branch=pr.head.ref,
                target_branch=pr.base.ref,
                source_sha=pr.head.sha,  # does this value change when new commits are added to source branch?
                merge_sha=pr.merge_commit_sha,
                created_at=pr.created_at,  # type: ignore
                merged_at=pr.merged_at,  # type: ignore
                updated_at=pr.updated_at,  # type: ignore
                # first_comment_at = ???
                is_merged=pr.merged,
                merged_by_username=pr.merged_by.login if pr.merged else None,
            )
            session.add(request)
            session.commit()

            n_requests += 1

        if n_requests > 0:
            logger.info(f"indexed {n_requests:3,} merge requests in the repository")

        return n_requests

    except GitCommandError as e:
        logger.warning(f"{e._cmdline} returned {e.stderr} for {log_url}")
    except DatabaseError as e:
        exc = traceback.format_exc()
        logger.warning(f"DatabaseError indexing repository {log_url} => {str(e)}\n{exc}")
    except Exception as e:  # pragma: no cover
        exc = traceback.format_exc()
        logger.warning(f"Exception indexing repository {log_url} => {str(e)}\n{exc}")

    return 0


def index_gitlab_merge_requests(session: Session, project: gl_projects.Project) -> int:
    n_requests = 0
    log_url = display_url(project.http_url_to_repo)

    try:
        repo = ensure_repository(session, project.http_url_to_repo, "gitlab")
        if repo is None:
            logger.info(f"### cannot create repostitory object for {log_url}")
            return 0

        if repo.is_active is False:
            logger.info(f"### skipping inactive repository {log_url}")
            return 0

        logger.info(f"starting to index merge requests for {log_url}")

        merge_requests = project.mergerequests.list(all=True)
        for mr in merge_requests:
            mr_id = str(mr.get_id())

            if mr.state not in ["closed", "merged"]:
                # index only closed or merged merge requests
                continue

            db_obj = session.query(MergeRequest).filter_by(request_id=mr_id, repo=repo).first()
            if db_obj is not None:
                # merge request already indexed
                continue

            is_merged, merged_by_username, merge_commit_sha = False, None, None
            if mr.state == "merged":
                is_merged, merged_by_username = True, mr.merge_user["username"]
                merge_commit_sha = mr.squash_commit_sha if mr.squash else mr.merge_commit_sha

            request = MergeRequest(
                repo=repo,
                request_id=mr_id,
                title=mr.title,
                state=mr.state,
                source_branch=mr.source_branch,
                target_branch=mr.target_branch,
                source_sha=mr.sha,
                merge_sha=merge_commit_sha,  # type: ignore
                created_at=gitlab_ts_to_datetime(mr.created_at),  # type: ignore
                merged_at=gitlab_ts_to_datetime(mr.merged_at),  # type: ignore
                updated_at=gitlab_ts_to_datetime(mr.updated_at),  # type: ignore
                is_merged=is_merged,
                merged_by_username=merged_by_username,
            )
            session.add(request)
            session.commit()

            n_requests += 1

        if n_requests > 0:
            logger.info(f"indexed {n_requests:3,} merge requests in the repository")

        return n_requests

    except GitCommandError as e:
        logger.warning(f"{e._cmdline} returned {e.stderr} for {log_url}")
    except DatabaseError as e:
        exc = traceback.format_exc()
        logger.warning(f"DatabaseError indexing repository {log_url} => {str(e)}\n{exc}")
    except Exception as e:  # pragma: no cover
        exc = traceback.format_exc()
        logger.warning(f"Exception indexing repository {log_url} => {str(e)}\n{exc}")

    return 0
