import os
import shlex

import pytest

from git_indexer.cli import main, parse_options


def test_cmdline_options():
    ## valid options
    args = parse_options(
        shlex.split("--mode commits --source gitlab --query stuff_that_i_care --filter '*' --mirror_path ~/tmp/mirror")
    )
    assert args.source == "gitlab" and args.mode == "commits" and len(args.mirror_path) > 1

    ## invalid options
    with pytest.raises(SystemExit):
        parse_options(shlex.split("--mode play"))


@pytest.mark.skipif(os.environ.get("GITLAB_TOKEN") is None, reason="gitlab token not available")
@pytest.mark.skipif(os.environ.get("OFFLINE_MODE") == "1", reason="running in offline mode")
def test_index_gitlab(tmp_path, sql_engine):
    argv = shlex.split(
        f"--mode commits --source gitlab --query securitybankph/rtd/bbx/samples/ --filter *sls-python-demo-4*  --mirror_path {tmp_path}"  # noqa: E501
    )
    main(argv=argv)


@pytest.mark.skipif(os.environ.get("OFFLINE_MODE") == "1", reason="running in offline mode")
def test_index_github(tmp_path, sql_engine):
    argv = shlex.split(f"--mode commits --source github --query sloppycoder/hello --mirror_path {tmp_path}")
    main(argv=argv)


def test_index_from_list(tmp_path, sql_engine):
    # the repo must be different from any other repos used in tests. otherwise it'll skew the commits count
    # and cause tests to fail
    argv = shlex.split(f"--mode commits --source list --query tests/data/test.lst --mirror_path {tmp_path}")
    main(argv=argv)


def test_cmdline_mode_mirror(mytest_dir, sql_engine, mocker):
    # running mirror only should only trigger calls to mirror_repo
    # no other calls
    m = mocks(mocker)  # noqa: VNE001

    argv = shlex.split(f"--mode mirror --source list --query {mytest_dir}/data/test.lst --mirror_path /blah")
    main(argv=argv)

    assert m.mirror_repo.call_count == 2
    m.index_commits.assert_not_called()
    m.index_github_pull_requests.assert_not_called()
    m.index_gitlab_merge_requests.assert_not_called()


def test_cmdline_mode_commits(mytest_dir, sql_engine, mocker):
    # running mirror will trigger calls to mirror_repo
    # and index_commits
    m = mocks(mocker)  # noqa: VNE001

    argv = shlex.split(f"--mode commits --source list --query {mytest_dir}/data/test.lst --mirror_path /blah")
    main(argv=argv)

    assert m.mirror_repo.call_count == 2
    assert m.index_commits.call_count == 2
    m.index_github_pull_requests.assert_not_called()
    m.index_gitlab_merge_requests.assert_not_called()


def test_cmdline_mode_requests(mytest_dir, sql_engine, mocker):
    # running merge will not call mirror_repo or index_commits
    m = mocks(mocker)  # noqa: VNE001

    argv = shlex.split(f"--mode requests --source list --query {mytest_dir}/data/test.lst --mirror_path /blah")
    main(argv=argv)

    m.mirror_repo.assert_not_called()
    m.index_commits.assert_not_called()
    m.index_github_pull_requests.assert_called_once()
    m.index_gitlab_merge_requests.assert_called_once()


def mocks(mocker):
    class MyMocks:
        def __init__(self, mocker):
            self.mirror_repo = mocker.patch(
                "git_indexer.cli.mirror_repo",
                return_value=("some_path", {}),
            )
            self.index_commits = mocker.patch(
                "git_indexer.cli.index_commits",
                return_value=(None, 0),
            )
            self.index_gitlab_merge_requests = mocker.patch(
                "git_indexer.cli.index_gitlab_merge_requests",
                return_value=1,
            )
            self.index_github_pull_requests = mocker.patch(
                "git_indexer.cli.index_github_pull_requests",
                return_value=1,
            )

    return MyMocks(mocker)
