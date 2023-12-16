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
# set optional environment variables
# only set it if testing with Gitlab and GCP is desired

GITLAB_TOKEN=glpat-xxxxxx

# index repos hosted on github, export result to CSV file then upload to Google Cloud Storage
# To be documented

```

## Run Unit Tests

```shell
# run test and generate coverage report in HTML format in htmlcov directory
pytest -v --cov . --cov-report html

```
