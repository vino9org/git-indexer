import argparse
import os

from alembic import command
from alembic.config import Config
from loguru import logger
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker

from .commit_indexer import index_commits
from .mirror import mirror_repo
from .request_indexer import index_github_pull_requests, index_gitlab_merge_requests
from .utils import (
    enumberate_from_file,
    enumerate_github_repos,
    enumerate_gitlab_repos,
    match_any,
)


def parse_options(argv):
    parser = argparse.ArgumentParser(prog="python -m git_indexer")
    parser.add_argument(
        "--all",
        action="store_true",
        default=False,
        help="index all commits, not just ones since last_indexed_at",
    )
    parser.add_argument(
        "--filter",
        required=False,
        default="*",
        help="Match repository patterns",
    )
    parser.add_argument(
        "--query",
        required=False,
        default="",
        help="Query for Github or Gitlab. For list, the path to the list file",
    )
    parser.add_argument(
        "--mode",
        choices=["commits", "requests", "mirror"],
        required=True,
        help="Index commits or merge/pull requests or just mirror repos without indexing",
    )
    parser.add_argument(
        "--source",
        choices=["github", "gitlab", "list"],
        required=True,
        help="The source to get repos from",
    )
    parser.add_argument(
        "--mirror_path",
        dest="mirror_path",
        required=False,
        default="",
        help="local path to store mirrors of remote repos",
    )

    ns = parser.parse_args(argv)

    if ns.mode != "requests" and ns.mirror_path == "":
        parser.error("--mirror_path is required except when mode is reuqests")

    return ns


def handle_options(options: argparse.Namespace, engine: Engine) -> None:
    logger.info(f"started command with: {options}")

    if options.source == "gitlab":
        enumerator = enumerate_gitlab_repos
    elif options.source == "github":
        enumerator = enumerate_github_repos  # type: ignore
    elif options.source == "list":
        enumerator = enumberate_from_file  # type: ignore
    else:
        logger.info(f"unknown source: {options.source}")
        return

    session = None
    try:
        Session = sessionmaker(bind=engine)
        session = Session()

        for repo_url, project in enumerator(options.query):
            if match_any(repo_url, options.filter):
                if options.source == "list":
                    repo_source = project["repo_source"]
                    is_private_repo = project["is_private"]
                    is_remote_repo = project["is_remote"]
                elif options.source == "gitlab":
                    is_private_repo = project.visibility == "private"
                    is_remote_repo = True
                    repo_source = "gitlab"
                elif options.source == "github":
                    is_private_repo = project.private
                    is_remote_repo = True
                    repo_source = "github"

                if options.mode == "requests":
                    if repo_source == "gitlab":
                        index_gitlab_merge_requests(session, project)
                    elif repo_source == "github":
                        index_github_pull_requests(session, project)
                    else:
                        logger.info(f"unknown repo_source: {repo_source} for {repo_url}")

                elif options.mode in ["commits", "mirror"]:
                    if is_remote_repo:
                        # create a local mirror of a remote repo
                        local_repo_path, _ = mirror_repo(
                            repo_url,
                            repo_source=options.source,
                            is_private_repo=is_private_repo,
                            dest_path=options.mirror_path,
                        )
                        if local_repo_path is None:
                            logger.warning(f"cannot create mirror for {repo_url}")
                            continue
                    else:
                        local_repo_path = repo_url

                    if options.mode == "commits":
                        index_commits(
                            session,
                            repo_url,
                            repo_source=repo_source,
                            local_repo_path=local_repo_path,
                            index_all=options.all,
                        )
                else:
                    logger.info(f"unknown mode: {options.mode}")
    finally:
        if session:
            session.close()


def create_sql_engine(run_check: bool = False) -> Engine:
    database_url = os.environ.get("DATABASE_URL", "")
    sql_engine = create_engine(database_url)
    logger.info(f"Initialized database engine {sql_engine.url}")

    if run_check:
        run_alembic_command("check")

    return sql_engine


def run_alembic_command(mode: str) -> None:
    """
    migrations.env.py will read env var DATABASE_URL
    and use it to run migarations
    """
    alembic_cfg = Config("alembic.ini")
    if mode == "upgrade":
        command.upgrade(alembic_cfg, "head")
    elif mode == "check":
        command.check(alembic_cfg)


def main(argv):
    options = parse_options(argv)
    sql_engine = create_sql_engine()
    handle_options(engine=sql_engine, options=options)
