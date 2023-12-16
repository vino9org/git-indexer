import os

import pytest

from git_indexer.utils import (
    clone_url2mirror_path,
    display_url,
    enumberate_from_file,
    enumerate_github_repos,
    enumerate_gitlab_repos,
    gitlab_ts_to_datetime,
    match_any,
    should_exclude_from_stats,
)

cwd = os.path.dirname(os.path.abspath(__file__))


def test_ignore_patterns():
    # vendered Go dependencies
    assert should_exclude_from_stats("vendor/librar/stuff/blah.go")
    assert should_exclude_from_stats("vendor/librar/stuff/README.md")

    # go module
    assert should_exclude_from_stats("go.sum")

    # binary files
    assert should_exclude_from_stats("lib/my_stupid_jar/blah.jar")
    assert should_exclude_from_stats("java.jar")
    assert should_exclude_from_stats("somepath/logo.png")
    assert should_exclude_from_stats("stuff.pdf")

    # Xcode project
    assert should_exclude_from_stats("Accelerator.xcodeproj/project.pbxproj")

    # Cocoa pod lock
    assert should_exclude_from_stats("Podfile.lock")
    assert should_exclude_from_stats("Pods/Firebase/CoreOnly/Sources/Firebase.h")
    assert should_exclude_from_stats("Something/Pods/Firebase.h")

    # yarn lock
    assert should_exclude_from_stats("yarn.lock")

    # npm lock
    assert should_exclude_from_stats("package-lock.json")
    assert should_exclude_from_stats("someapp/package-lock.json")

    # npm modules
    assert should_exclude_from_stats("node_modules/.app.js")
    assert should_exclude_from_stats("someapp/node_modules/.app.js")

    # Next.js build
    assert should_exclude_from_stats("someapp/.next/_app.js")
    assert should_exclude_from_stats("webretail/.next/static/chunks/pages/_app.js")
    assert should_exclude_from_stats("webretail/.next/static/webpack/pages/indexupdate.js")
    assert should_exclude_from_stats("webretail/.next/server/pages/_document.js")
    assert should_exclude_from_stats("common/assets/Styling/_mixins.scss")

    # IDE/Editor files
    assert should_exclude_from_stats(".vscode/settings.json")
    assert should_exclude_from_stats(".idea/misc.xml")

    # build output
    assert should_exclude_from_stats("target/output/pom.xml")
    assert should_exclude_from_stats("target/output/pom.xml")

    # backkup files
    assert should_exclude_from_stats("src/pom.xml.bak")

    # devcontainer stuff
    assert should_exclude_from_stats(".devcontainer/docker-compose.yml")
    assert should_exclude_from_stats(".devcontainer/local-data/keycloak-data.json")

    assert not should_exclude_from_stats("src/main/my/company/package/Application.java")
    assert not should_exclude_from_stats("src/resources/application.yaml")
    assert not should_exclude_from_stats("Something/another/Pods/Firebase.h")
    assert not should_exclude_from_stats("package.json")
    assert not should_exclude_from_stats("node_modules.txt")
    assert not should_exclude_from_stats(".next.d")

    # not real files but similiar to IDE stuff
    assert not should_exclude_from_stats("idea/misc.xml")
    assert not should_exclude_from_stats("vscode/settings.json")


def test_match_any():
    assert match_any("/Users/lee/tmp/shared/bbx/company/bbx-cookiecutter-springboot3.git", "*/bbx/*/bbx*")
    assert not match_any("/Users/lee/tmp/shared/bbx/cookiecutter-springboot3.git", "*/bbx/bbx*")


def test_display_url():
    assert (
        display_url(
            "https://gitlab.com/securemyphbank/shared/pro/devops/gitlab-ci/shared-gitlab-blueprints/java-ms-blueprint"
        )
        == "/se...evops/gitlab-ci/shared-gitlab-blueprints/java-ms-blueprint"
    )

    assert display_url("https://github.com/sloppy_coder/xyz.git") == "/sloppy_coder/xyz"

    assert (
        display_url("git@gitlab.com:securemyphbank/rtd/pro/local-payment-service-chart.git", 64)
        == "securemyphbank/rtd/pro/local-payment-service-chart"
    )


def test_gitlab_ts_to_datetime():
    assert gitlab_ts_to_datetime(None) is None
    dt = gitlab_ts_to_datetime("2021-08-31T09:00:00.000Z")
    assert (dt.year, dt.month, dt.second) == (2021, 8, 0)
    assert dt.tzinfo.tzname(dt) == "UTC"


def test_clone_url2mirror_path():
    assert ("/parent_dir/company/project/repo.git") == clone_url2mirror_path(
        "https://user:pass@gitlab.com/company/project/repo", "/parent_dir"
    )

    assert ("/parent_dir/project/repo.git") == clone_url2mirror_path(
        "https://github.com/project/repo.git", "/parent_dir"
    )

    assert ("~/parent_dir/company/project/repo.git") == clone_url2mirror_path(
        "git@server.net:company/project/repo.git", "~/parent_dir"
    )

    assert ("some_path/parent_dir/project/repo1.git") == clone_url2mirror_path(
        "project/repo1.git", "some_path/parent_dir"
    )
    assert ("/parent_dir/project/repo1.git") == clone_url2mirror_path("/home/git/project/repo1.git", "/parent_dir")


@pytest.mark.skipif(os.environ.get("GITLAB_TOKEN") is None, reason="gitlab token not available")
@pytest.mark.skipif(os.environ.get("OFFLINE_MODE") == "1", reason="running in offline mode")
def test_enumerate_gitlab_repos():
    repos = list(enumerate_gitlab_repos("hello-api"))
    assert len(repos) > 0
    assert list(repos)[0][1].visibility is not None


@pytest.mark.skipif(os.environ.get("OFFLINE_MODE") == "1", reason="running in offline mode")
def test_enumerate_github_repos():
    repos = list(enumerate_github_repos("sloppycoder/hello"))
    assert len(repos) > 0
    assert list(repos)[0][1].private is not None


def test_enumerate_from_file(mytest_dir):
    repos = list(enumberate_from_file(f"{mytest_dir}/data/test.lst"))
    assert len(repos) == 2

    repo1 = list(repos[0])[1]
    assert repo1["is_remote"] is True and repo1["repo_source"] == "gitlab" and repo1["is_private"] is True

    repo2 = list(repos[1])[1]
    assert repo2["is_remote"] is True and repo2["repo_source"] == "github" and repo2["is_private"] is False
