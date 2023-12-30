import os

import pytest

from git_indexer.models import MergeRequest, Repository
from git_indexer.request_indexer import index_merge_requests


@pytest.mark.skipif(os.environ.get("OFFLINE_MODE") == "1", reason="running in offline mode")
def test_index_github_pull_requests(session, github):
    git_repo = github.get_repo("sloppycoder/hello")
    assert index_merge_requests(session, "github", git_repo) > 0

    repo = session.query(Repository).filter_by(clone_url=git_repo.clone_url, repo_type="github").first()
    assert repo is not None

    pr = session.query(MergeRequest).filter_by(repo=repo, request_id="1").first()
    assert pr.request_id == "1" and pr.state == "closed" and pr.is_merged

    # inex for the 2nd time will out create more records
    assert index_merge_requests(session, "github", git_repo) == 0


@pytest.mark.skipif(os.environ.get("GITLAB_TOKEN") is None, reason="gitlab token not available")
@pytest.mark.skipif(os.environ.get("OFFLINE_MODE") == "1", reason="running in offline mode")
def test_index_gitlab_merge_requests(session, gitlab):
    project = gitlab.projects.get("vino9/test-project-1")
    assert index_merge_requests(session, "gitlab", project) > 0

    repo = session.query(Repository).filter_by(clone_url=project.http_url_to_repo, repo_type="gitlab").first()
    assert repo is not None

    mr = session.query(MergeRequest).filter_by(repo=repo, request_id="1").first()
    assert mr.request_id == "1" and mr.state == "merged" and mr.target_branch == "main"

    # inex for the 2nd time will out create more records
    assert index_merge_requests(session, "gitlab", project) == 0
