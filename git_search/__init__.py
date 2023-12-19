import os
import re
import sys
import warnings

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request
from loguru import logger
from sqlalchemy.orm import joinedload, sessionmaker

# from flask_sqlalchemy import SQLAlchemy
from werkzeug.middleware.proxy_fix import ProxyFix
from wtforms.fields import StringField, SubmitField

from git_indexer.cli import create_sql_engine
from git_indexer.models import Author, Commit, Repository

with warnings.catch_warnings():
    # these packages uses flask.Markup
    # suppress the warning when running tests
    warnings.simplefilter("ignore")
    from flask_bootstrap import Bootstrap5  # noqa: E402, F401
    from flask_wtf import FlaskForm  # noqa: E402

__MAX_ITEMS__ = 50
__EMPTY_RESULT__ = {"commits": [], "authors": [], "repos": []}  # type: ignore

logger.remove()
logger.add(sys.stdout, level="INFO")


def init_app() -> Flask:
    cwd = os.path.dirname(os.path.abspath(__file__))
    template_folder = os.path.abspath(f"{cwd}/../templates")
    app = Flask(__name__, template_folder=template_folder)
    secret_key = os.environ.get("SECRET_KEY")
    app.config["SECRET_KEY"] = secret_key if secret_key else os.urandom(32)
    app.logger = logger

    if os.environ.get("KUBERNETES_SERVICE_HOST"):
        logger.info("running in kubernetes, using proxy fix")
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)  # type: ignore

    return app


load_dotenv()

app = init_app()
bootstrap = Bootstrap5(app)

__sql_engine__ = None  # type: ignore


def get_session():
    global __sql_engine__
    if __sql_engine__ is None:
        if os.environ.get("DATABASE_URL") is None:
            load_dotenv
        __sql_engine__ = create_sql_engine(run_check=True)
        assert __sql_engine__ is not None, "SQL engine not set"

    session_maker = sessionmaker(bind=__sql_engine__)
    return session_maker()


class SearchForm(FlaskForm):
    query = StringField(label="Enter a git commit hash, email address or repository name")
    search = SubmitField("Search")


@app.route("/")
def index():
    return redirect("search")


@app.route("/search", methods=["GET", "POST"])
def search():
    params = {}

    # Handle GET request
    if request.method == "GET":
        params = request.args.to_dict()
    elif request.method == "POST":
        params = request.form.to_dict()

    query = params.get("query")

    if query is None or len(query) < 4:
        if query:
            flash("Valid search term should be longer than 4 characters", "danger")
        return render_template("search.html", result=__EMPTY_RESULT__, form=SearchForm())

    if "@" not in query and re.match(r"[0-9a-f]{7}", query):
        # looks like a git hash
        result = search_commits("sha", query)
    elif "@" in query and (match := re.search(r"\b(\S+@\S+)\b", query)):
        result = search_commits("email", match[0])
    else:
        # assume it's a repo name
        result = search_commits("repo", query)

    return render_template("search.html", result=result, form=SearchForm())


def search_commits(mode: str, query: str):
    with get_session() as session:
        result = __EMPTY_RESULT__

        if mode == "sha":
            commits = (
                session.query(Commit)
                .options(joinedload(Commit.repos))
                .filter(Commit.sha.like(f"%{query}%"))
                .limit(__MAX_ITEMS__)
                .all()
            )
            result = {"commits": commits}

        elif mode == "email":
            # query for authors. is_parent True comes first
            authors = session.query(Author).filter(Author.email.like(f"%{query}%")).all()
            result = {"authors": authors}
            # TODO: handle parent_id
            if len(authors) == 1:
                commits = (
                    session.query(Commit)
                    .options(joinedload(Commit.repos))
                    .filter(Commit.author == authors[0])
                    .limit(__MAX_ITEMS__)
                    .all()
                )
                result["commits"] = commits

        elif mode == "repo":
            repos = session.query(Repository).filter(Repository.clone_url.like(f"%{query}%")).limit(__MAX_ITEMS__).all()
            result = {"repos": repos}
            if len(repos) == 1:
                commits = (
                    session.query(Commit)
                    .options(joinedload(Commit.repos))
                    .filter(Commit.repos.contains(repos[0]))
                    .limit(__MAX_ITEMS__)
                    .all()
                )
                result["commits"] = commits

        return result
