import os

import pytest

from git_indexer.mirror import mirror_repo


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
