# Utlity that scan git repositories and extract metrics

## Setup the environment

```shell

# easist way, use jetpack.io devbox
devbox shell

# or install python and poetry, then
poetry shell
poetry install

# or the use plain old venv
python -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

```

## Run

```shell
# create a .env file with the following content

GITLAB_TOKEN=glpat-xxxxxx
GITHUB_TOKEN=ghat-yyyyy

DATABASE_URL=postgresql+psycopg://host:port/db
PGUSER=user
PGPASSWORD=pass

# database used for testing. the database user must have CREATEDB privilege.
# when not set, a sqlite3 database will be used for each test run.
TEST_DATABASE_URL=postgresql+psycopg://host:port/db_test

# end of .env

# run code to create a local mirror of remote repos hosted on Github or Gitlab and index the commits
python -u -m git_indexer --mode=commits --source gitlab --query "/organization/" --filter="*" --mirror_path /vol/mirror

# run code to index merge requests/pull requests for remote repos hosted on Github or Gitlab
python -u -m git_indexer --mode=requests --source gitlab --query "/organization/" --filter="*"

```

## Run Unit Tests

```shell
# run test and generate coverage report in HTML format in htmlcov directory
pytest -v --cov . --cov-report term

```
