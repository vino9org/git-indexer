import os

import git
import pytest

from git_indexer.mirror import mirror_repo, update_remote_url


@pytest.mark.skipif(os.environ.get("OFFLINE_MODE") == "1", reason="running in offline mode")
def test_mirror_repo(tmp_path):
    parent_path = tmp_path.as_posix()

    # 1st run should trigger a git clone using git clone --mirror
    mirror_path, is_new = mirror_repo(
        "https://github.com/sloppycoder/hello.git",
        repo_source="github",
        is_private_repo=False,
        dest_path=parent_path,
    )
    assert is_new
    assert os.path.isfile(mirror_path + "/HEAD")

    # 2nd run should just git fetch --prune. by default no output is the repo is up-to-date
    mirror_path, is_new = mirror_repo(
        "https://github.com/sloppycoder/hello.git",
        repo_source="github",
        is_private_repo=False,
        dest_path=parent_path,
    )
    assert not is_new
    assert os.path.isfile(mirror_path + "/HEAD")


def test_update_remote_url(local_repo):
    old_gitlab_token = os.environ.get("GITLAB_TOKEN")
    os.environ["GITLAB_TOKEN"] = "fake_token"

    try:
        local_mirror_path = local_repo + "/test_mirror"
        assert update_remote_url(local_mirror_path, "gitlab") is True

        repo = git.Repo(local_mirror_path)
        new_url = repo.remote().url
        assert new_url.startswith("https://oauth2:fake_token")

    finally:
        if old_gitlab_token:
            os.environ["GITLAB_TOKEN"] = old_gitlab_token
