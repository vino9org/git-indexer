import os
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from github import Auth, Github
from gitlab import Gitlab
from loguru import logger
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy_utils import create_database, database_exists, drop_database

# Add the parent directory to the path so we can import the module git_indexer
cwd = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(f"{cwd}/.."))

from git_indexer.cli import create_sql_engine, run_alembic_command  # noqa: E402
from git_indexer.models import (  # noqa E402
    Author,
    Commit,
    CommittedFile,
    MergeRequest,
    Repository,
)
from git_indexer.utils import is_online  # noqa: E402

# logger.remove()  # remove default hanlders
# logger.add(sys.stdout, level="INFO", filter="*")

os.environ["OFFLINE_MODE"] = "0" if is_online() else "1"
os.environ["TESTING"] = "1"


@pytest.fixture
def mytest_dir():
    yield cwd


def seed_data(session: Session):
    now = datetime.now().replace(tzinfo=timezone.utc)

    me = Author(name="me", email="mini@me")
    commit1 = Commit(
        sha="feb3a2837630c0e51447fc1d7e68d86f964a8440",
        author=me,
        created_at=now,  # type: ignore
        created_at_tz=now,  # type: ignore
    )
    commit2 = Commit(
        sha="ee474544052762d314756bb7439d6dab73221d3d",
        author=me,
        created_at=now,  # type: ignore
        created_at_tz=now,  # type: ignore
    )
    commit3 = Commit(
        sha="e2c8b79813b95c93e5b06c5a82e4c417d5020762",
        author=me,
        created_at=now,  # type: ignore
        created_at_tz=now,  # type: ignore
    )

    repo1 = Repository(
        clone_url="git@github.com:super/repo.git",
        repo_type="github",
        repo_name="repo",
        commits=[commit1, commit2],
    )
    repo2 = Repository(
        clone_url="https://gitlab.com/dummy/repo.git",
        repo_type="gitlab",
        repo_name="repo",
        commits=[commit1, commit3],
    )

    commit1.repos = [repo1, repo2]
    commit2.repos = [repo1]
    commit3.repos = [repo2]

    file1 = CommittedFile(
        file_path="README.md",
        file_name="README.md",
        change_type="ADD",
        commit=commit1,
    )
    file2 = CommittedFile(
        file_path="package.json",
        file_name="package.json",
        change_type="UPDATE",
        commit=commit1,
    )
    file3 = CommittedFile(
        file_path="/src/main/java/com/company/MainApplication.java",
        file_name="MainApplication.java",
        change_type="DELETE",
        commit=commit2,
    )
    file4 = CommittedFile(
        file_path="app/App.js",
        file_name="App.js",
        change_type="UPDATE",
        commit=commit1,
    )

    mr1 = MergeRequest(
        request_id="MR1",
        state="OPEN",
        title="Merge Request 1",
        source_branch="feature/feature-1",
        target_branch="develop",
        repo=repo1,
    )

    mr2 = MergeRequest(
        request_id="MR2",
        state="OPEN",
        title="Merge Request 2",
        source_branch="feature/feature-2",
        target_branch="develop",
        repo=repo1,
    )

    session.add_all([me, repo1, repo2, file1, file2, file3, file4, mr1, mr2])
    session.commit()


@pytest.fixture(scope="session")
def tmp_db(tmp_path_factory: pytest.TempPathFactory):
    basetemp = tmp_path_factory.getbasetemp()
    temp_db_path = basetemp / "test.db"

    os.environ["DATABASE_URL"] = f"sqlite:///{temp_db_path}"

    yield temp_db_path

    if os.path.isfile(temp_db_path):
        os.remove(temp_db_path)


@pytest.fixture(scope="session")
def sql_engine(tmp_path_factory):
    test_db_url = os.environ.get("TEST_DATABASE_URL")
    if test_db_url is None:
        test_db_url = f"sqlite:///{tmp_path_factory.getbasetemp()}/test.db"

    if not database_exists(test_db_url):
        logger.info(f"creating test database {test_db_url}")
        create_database(test_db_url)

    os.environ["DATABASE_URL"] = test_db_url
    sql_engine = create_sql_engine()
    run_alembic_command("upgrade")

    # seed test data
    with sessionmaker(bind=sql_engine)() as session:
        seed_data(session)

    yield sql_engine

    if test_db_url.startswith("postgres") and os.environ.get("KEEP_TEST_DB", "").upper() not in ["1", "Y"]:
        logger.info(f"dropping test database {test_db_url}")
        drop_database(test_db_url)


@pytest.fixture(scope="session")
def session(sql_engine: Engine):
    Session = sessionmaker(bind=sql_engine)
    session = Session()

    yield session

    session.close()


@pytest.fixture(scope="session")
def gitlab():
    private_token = os.environ.get("GITLAB_TOKEN")
    if private_token:
        yield Gitlab("https://gitlab.com", private_token=private_token, per_page=100)
    else:
        yield None


@pytest.fixture(scope="session")
def github():
    access_token = os.environ.get("GITHUB_TOKEN")
    if access_token:
        yield Github(auth=Auth.Token(access_token))
    else:
        yield Github()


@pytest.fixture
def local_repo(tmp_path: Path):
    repo_base = tempfile.mkdtemp(dir=tmp_path)
    zip_file_path = os.path.abspath(f"{cwd}/data/test_repos.zip")
    with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
        zip_ref.extractall(repo_base)

    yield repo_base

    shutil.rmtree(repo_base)


@pytest.fixture
def mirror_parent_path(tmp_path: Path):
    yield (tmp_path / "mirror").as_posix()
