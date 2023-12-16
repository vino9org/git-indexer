import random
import string
from datetime import datetime

import git
from sqlalchemy import text

from git_indexer.commit_indexer import index_commits
from git_indexer.models import (
    ensure_repository,
    repo_commit_hashes,
    repo_to_commit_table,
)


def test_index_local_repo(session, local_repo, mirror_parent_path):
    """
    there're 2 test repos
    repo1 has 2 commits
    repo1_fork is a clone of repo1, then add 1 more commits, so totaly 3 commits
    """

    rows_before = _get_row_count_from_join_table_(session)

    # test 1:  index a new repo repo1
    repo1 = local_repo + "/repo1"
    repo_obj, n_commits = index_commits(session, repo1, local_repo_path=repo1, repo_source="local")
    assert n_commits == 2
    repo1_sha = repo_commit_hashes(repo_obj)
    assert len(repo1_sha) == 2

    # test 2: index repo1 again
    # no new commits will be added
    repo_obj, n_commits = index_commits(session, repo1, local_repo_path=repo1, repo_source="local")
    assert n_commits == 0
    repo1_sha = repo_commit_hashes(repo_obj)
    assert len(repo1_sha) == 2

    # test 3: index repo1_fork
    # only the 1 new commit will be added to commit table
    # the commits in original repo should all be in the fork
    # as a side effect, this also tests the increment mirror update for repo1_fork too
    repo1_fork = local_repo + "/repo1_fork"
    repo_obj, n_commits = index_commits(session, repo1_fork, local_repo_path=repo1_fork, repo_source="local")

    assert n_commits == 3
    repo1_fork_sha = repo_commit_hashes(repo_obj)
    assert len(repo1_fork_sha) == 3
    assert all(sha in repo1_fork_sha for sha in repo1_sha)
    # after index the repo object in db should have valid timestamps
    repo1_fork_obj = ensure_repository(session, repo1_fork, "local")
    assert repo1_fork_obj.last_indexed_at
    # the actual commit date is "2023-07-07T15:59:06+08:00", we use UTC time without timezone
    known_last_commit_dt = datetime.strptime("2023-07-07T07:59:06", "%Y-%m-%dT%H:%M:%S")
    assert repo1_fork_obj.last_commit_at == known_last_commit_dt

    # test4:
    # add some random commits to the repo, then index it
    # the new commits should be equal to the number of random commits added
    # the last_commit_at should be updated, new commits will be indexed
    new_commit_dt = datetime.utcnow()
    n_new_commits = _add_random_commit_(repo1_fork)
    repo_obj, n_commits = index_commits(session, repo1_fork, repo_source="local", local_repo_path=repo1_fork)

    assert n_commits == n_new_commits
    assert abs((repo1_fork_obj.last_commit_at - new_commit_dt).total_seconds()) < 60

    # verify the record count in many-to-many join table
    rows_after = _get_row_count_from_join_table_(session)
    assert rows_after - rows_before == 5 + n_new_commits


def test_index_empty_repo(session, local_repo, mirror_parent_path):
    """
    empty_repo is empty, no commit after git init.
    """
    # empty repo should not throw any exception
    empty_repo = local_repo + "/empty_repo"
    _, n_commits = index_commits(session, empty_repo, local_repo_path=empty_repo, repo_source="local")

    assert n_commits == 0


def _add_random_commit_(repo_path: str):
    """create a few random commit into a local repo"""
    n_rand = random.randint(2, 6)

    for _ in range(n_rand):
        random_str = "".join(random.choice(string.ascii_lowercase) for i in range(3))
        with open(repo_path + f"/random{random_str}.txt", "w") as f:
            f.write(f"random content:{random_str}")

        repo = git.Repo(repo_path)
        repo.git.add(update=True)  # Equivalent to `git add -u`
        repo.git.add(A=True)  # To also add untracked files, equivalent to `git add .`
        repo.index.commit("some random commit")

    return n_rand


def _get_row_count_from_join_table_(session):
    result = session.execute(text("select count(*) from " + repo_to_commit_table.name)).fetchone()
    return result[0] if result else 0
