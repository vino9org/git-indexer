import traceback
from typing import Any

from git import GitCommandError
from github import Repository as github_repo
from gitlab.v4.objects import projects as gl_projects
from loguru import logger
from psycopg import DatabaseError
from sqlalchemy.orm import Session

from git_indexer.models import MergeRequest, Repository, ensure_repository
from git_indexer.utils import display_url, gitlab_ts_to_datetime


def create_new_request(session: Session, obj_from_api: Any, repo: Repository) -> MergeRequest:
    if repo.repo_type == "github":
        # TODO: pr.created_at is a naive datetime object, timezone is assumed to be UTC
        pr = obj_from_api
        request = MergeRequest(
            repo=repo,
            request_id=str(pr.number),
            title=obj_from_api.title,
            state=obj_from_api.state,
            source_branch=pr.head.ref,
            target_branch=pr.base.ref,
            source_sha=pr.head.sha,  # does this value change when new commits are added to source branch?
            merge_sha=pr.merge_commit_sha,
            created_at=pr.created_at,
            merged_at=pr.merged_at,
            updated_at=pr.updated_at,
            # first_comment_at = ???
            is_merged=pr.merged,
            merged_by_username=pr.merged_by.login if pr.merged else None,
        )

    elif repo.repo_type == "gitlab":
        mr = obj_from_api

        is_merged, merged_by_username, merge_commit_sha = False, None, None
        if mr.state == "merged":
            is_merged, merged_by_username = True, mr.merge_user["username"]
            merge_commit_sha = mr.squash_commit_sha if mr.squash else mr.merge_commit_sha

        request = MergeRequest(
            repo=repo,
            request_id=str(mr.get_id()),
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
    else:
        raise ValueError("unknown type for input objevct")

    session.add(request)
    session.commit()

    return request


def requests_to_index(repo_type: str, project: gl_projects.Project | github_repo.Repository):
    if repo_type == "github":
        return project.get_pulls(state="closed")
    elif repo_type == "gitlab":
        requests = project.mergerequests.list(all=True)  # type: ignore
        return [req for req in requests if req.state in ["closed", "merged"]]
    else:
        raise ValueError(f"unknown repo_type {repo_type}")


def index_merge_requests(
    session: Session, repo_type: str, project: gl_projects.Project | github_repo.Repository
) -> int:
    n_requests = 0

    if repo_type == "gitlab":
        clone_url = project.http_url_to_repo  # type: ignore
        log_url = display_url(clone_url)
    elif repo_type == "github":
        log_url = display_url(project.clone_url)
        clone_url = project.clone_url
    else:
        raise ValueError(f"unknown repo_type {repo_type}")

    try:
        repo = ensure_repository(session, clone_url, repo_type)
        if repo is None:
            logger.info(f"### cannot create repostitory object for {log_url}")
            return 0

        if repo.is_active is False:
            logger.info(f"### skipping inactive repository {log_url}")
            return 0

        logger.info(f"starting to index merge requests for {log_url}")

        for req in requests_to_index(repo_type, project):
            if repo_type == "gitlab":
                req_id = str(req.get_id())
            else:
                req_id = str(req.number)

            db_obj = session.query(MergeRequest).filter_by(request_id=req_id, repo=repo).first()
            if db_obj is None:
                create_new_request(session, req, repo)
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
