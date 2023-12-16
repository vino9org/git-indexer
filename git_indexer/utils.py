import fnmatch
import os
import pathlib
import re
import urllib
from datetime import datetime, timezone
from typing import Any, Iterator, Optional

from github import Auth, BadCredentialsException, Github
from gitlab import Gitlab
from loguru import logger

# files matches any of the regex will not be counted
# towards commit stats
_IGNORE_PATTERNS_ = [
    re.compile(
        "^(vendor|Pods|target|YoutuOCWrapper|vos-app-protection|vos-processor|\\.idea|\\.vscode)/."  # noqa: E501
    ),
    re.compile("^[a-zA-Z0-9_]*?/Pods/"),
    re.compile("^.*(xcodeproj|xcworkspace)/."),
    re.compile(r".*\.(jar|pbxproj|lock|bk|bak|backup|class|swp|sum|pdf|png)$"),
    re.compile(r"^.*/?package-lock\.json$"),
    re.compile(r"^.*/?(\.next|node_modules|\.devcontainer)(/|$).*"),
    re.compile(r"(^|.*/)_.*\.(js|scss)$"),
]


def match_any(path: str, patterns: str) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns.split(","))


def should_exclude_from_stats(path: str) -> bool:
    """
    return true if the path should be ignore
    for calculating commit stats
    """
    for regex in _IGNORE_PATTERNS_:
        if regex.match(path):
            return True
    return False


def __shorten__(path: str, max_lenght: int) -> str:
    if len(path) > max_lenght:
        return path[:3] + "..." + path[(max_lenght - 6) * -1 :]
    else:
        return path


def display_url(clone_url: str, max_length: int = 64) -> str:
    url = re.sub(r"https?://[^\/]+", "", clone_url)  # remove http(s)://host portion of the url
    url = re.sub(r"git@.*:", "", url)  # remove the git@host: portion of the url
    url = __shorten__(url, max_length)
    return re.sub(r".git$", "", url)


def gitlab_ts_to_datetime(ts: None | str) -> None | datetime:
    """
    gitlab api returns timestamp is string format in UTC
    convert it to timezone aware datetime object
    """
    if ts is None:
        return None
    else:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%fz").replace(tzinfo=timezone.utc)


def clone_url2mirror_path(clone_url: str, dest_path: str) -> str:
    """
    convert clone url to a path to be used for local mirror
    """
    if clone_url.startswith("http"):
        # returns the namespace/project/repo in https://user:pass@somethig.com/namespace/project/repo
        path = "/".join(clone_url.split("/")[3:])
    elif clone_url.startswith("git@"):
        # returns the namespace/project/repo in git@somethig.com:namespace/project/repo
        path = clone_url.split(":")[1]
    else:
        # treat clone_url as a local repo
        full_path = pathlib.PurePath(clone_url)
        path = full_path.parents[0].name + "/" + full_path.name  # the parent directory of clone_url

    if not path.endswith(".git"):
        path = path + ".git"

    return f"{dest_path}/{path}"


def enumerate_gitlab_repos(
    query: str, private_token: Optional[str] = None, url: str = "https://gitlab.com"
) -> Iterator[tuple[str, Any]]:
    if private_token is None:
        private_token = os.environ.get("GITLAB_TOKEN")
        if not private_token:
            logger.info("GITLAB_TOKEN environment variable not set")
            return

    gl = Gitlab(url, private_token=private_token, per_page=20)
    for project in gl.search(scope="projects", search=query, iterator=True):
        repo = gl.projects.get(project["id"])
        clone_url = repo.http_url_to_repo
        yield clone_url, repo


def enumerate_github_repos(
    query: str, access_token: Optional[str] = None, useHttpUrl: bool = False
) -> Iterator[tuple[str, Any]]:
    if access_token is None:
        access_token = os.environ.get("GITHUB_TOKEN")

    try:
        gh = Github(auth=Auth.Token(access_token)) if access_token else Github()
        for repo in gh.search_repositories(query=query):
            clone_url = repo.clone_url
            yield clone_url, repo
    except BadCredentialsException as e:
        logger.info(f"authentication error => {e}")
    except Exception as e:
        logger.info(f"gitlab search {query} error {type(e)} => {e}")


def enumberate_from_file(source_file: str) -> Iterator[tuple[str, Any]]:
    """
    enumberate repos from a list file, each line in the file is
    url,is_private,repo_source
    """
    with open(source_file, "r") as f:
        for line in f.readlines():
            line = line.strip()
            if not line.startswith("#") and len(line) > 6:
                parts = line.strip().split(",")

                url = parts[0].lower()
                private_flag = parts[1].lower() if len(parts) > 1 else "n"

                if "github.com" in url:
                    source = "github"
                elif "gitlab.com" in url:
                    source = "gitlab"
                else:
                    source = parts[2].lower() if len(parts) > 2 else "local"

                project = {
                    "clone_url": url,
                    "is_private": private_flag == "y",
                    "repo_source": source,
                    "is_remote": source != "local",
                }

                yield parts[0], project


def is_online() -> bool:
    try:
        urllib.request.urlopen("https://github.com", timeout=1)
        return True
    except urllib.error.URLError:
        return False
