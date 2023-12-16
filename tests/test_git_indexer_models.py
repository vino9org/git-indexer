from git_indexer.models import (
    Author,
    Commit,
    Repository,
    ensure_repository,
    repo_commit_hashes,
)


def test_query_models(session):
    author = session.query(Author).filter_by(name="me").first()
    assert author.id is not None
    assert len(author.commits) == 3

    commit = session.query(Commit).filter_by(sha="feb3a2837630c0e51447fc1d7e68d86f964a8440").first()
    assert commit is not None
    assert commit.author_id == author.id
    assert len(commit.files) == 3

    # test commit to repo many-to-many relation
    repos = commit.repos  # Assuming you have set up the relationship correctly
    assert len(repos) == 2
    assert repos[0].clone_url == "git@github.com:super/repo.git"

    commit2 = session.query(Commit).filter_by(sha="ee474544052762d314756bb7439d6dab73221d3d").first()
    assert commit2 is not None and len(commit2.repos) == 1

    # test repo to commit many-to-many relation
    repo = session.query(Repository).filter_by(clone_url="git@github.com:super/repo.git").first()
    assert repo is not None
    assert len(repo.commits) == 2

    # test repo to merge request one-to-many relation
    requests = repo.merge_requests
    assert len(requests) == 2
    assert requests[0].request_id == "MR1"


def test_ensure_repository(session):
    repo1 = ensure_repository(session, "git@github.com:super/repo.git", "github")
    assert repo1 is not None

    repo2 = ensure_repository(session, "https://github.com/sloppycoder/git-indexer.git", "github")
    assert repo2 is not None
    assert repo2.id > 2  # this should be the 3rd repo record


def test_repo_commit_hashes(session):
    repo = ensure_repository(session, "git@github.com:super/repo.git", "github")
    assert repo is not None

    hashes = repo_commit_hashes(repo)
    assert len(hashes) == 2
