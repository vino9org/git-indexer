import os
import shlex
import subprocess

from loguru import logger

from .utils import clone_url2mirror_path, display_url


def run(command: str) -> bool:
    ret = subprocess.call(shlex.split(command))
    if ret == 0:
        return True
    else:
        logger.warning(f"*** returned code {ret} for {command}")
        return False


def mirror_repo(
    clone_url: str, repo_source: str, is_private_repo: bool, dest_path: str, overwrite: bool = False
) -> tuple[str | None, bool]:
    """
    create a local mirror (as a bare repo) of a remote repo
    returns a tuple:
      mirror_path: path of mirror repo if a mirror is created or updated, None if failed
      is_new: True if a new mirror is created, False if an existing mirror is updated

    """
    repo_dir = os.path.abspath(clone_url2mirror_path(clone_url, dest_path))
    log_url = display_url(clone_url)

    cwd = os.getcwd()
    try:
        if os.path.isdir(repo_dir) and os.path.isfile(f"{repo_dir}/HEAD"):
            # mirror directory exists and seems like a legit bare git repo
            os.chdir(repo_dir)
            if run("git fetch --prune"):
                logger.info(f"Updated existing repo {repo_dir} from {log_url}")
                return repo_dir, False
            else:
                logger.warning(f"unable to fetch {log_url}")
                return None, False

        elif os.path.isdir(repo_dir) and overwrite:
            # mirror directory exists but not a git repo. we overwrite it
            logger.info(f"{repo_dir} exists but is not a bare git repo, removing all contents")
            run(f"rm -rf {repo_dir}")
        else:
            # repo_dir does not exist, create it.
            # git clone --mirror won't complain if the target already exists but is empty
            os.makedirs(repo_dir, exist_ok=False)

        os.chdir(repo_dir + "/..")

        if is_private_repo:
            full_url = url_with_token(clone_url, repo_source)
        else:
            full_url = clone_url
        if run(f"git clone --mirror {full_url}") and os.path.isfile(f"{repo_dir}/HEAD"):
            logger.info(f"Created new mirror in {repo_dir} for {log_url}")
            return repo_dir, True
        else:
            logger.warning(f"unable to clone {log_url}")
            return None, False

    finally:
        os.chdir(cwd)


def url_with_token(clone_url: str, repo_source: str) -> str:
    # add access token to http url for repos that needs autentication
    full_url = clone_url

    if clone_url.startswith("http"):
        if repo_source == "github" or clone_url.startswith("https://github.com"):
            access_token = os.environ.get("GITHUB_TOKEN")
            if access_token:
                full_url = clone_url.replace("https://", f"https://{access_token}:")
        elif repo_source == "gitlab" or clone_url.startswith("https://gitlab.com"):
            access_token = os.environ.get("GITLAB_TOKEN")
            if access_token:
                full_url = clone_url.replace("://", f"://oauth2:{access_token}@")

    return full_url
