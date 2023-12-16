from git_search import app


def test_search_page(sql_engine):
    response = app.test_client().get("/search")
    assert response.status_code == 200


def test_search_by_commit(sql_engine):
    query = "964a8440"
    with app.test_client() as client:
        response = client.post(
            "/search",
            data={"query": query},
            follow_redirects=True,
            content_type="application/x-www-form-urlencoded",
        )
        assert response.status_code == 200
        assert query.encode("utf-8") in response.data


def test_search_by_repo_name_multiple_match(sql_engine):
    query = "repo"
    with app.test_client() as client:
        response = client.post(
            "/search",
            data={"query": query},
            follow_redirects=True,
            content_type="application/x-www-form-urlencoded",
        )
        assert response.status_code == 200
        assert "super/repo".encode("utf-8") in response.data


def test_search_by_repo_name_single_match(sql_engine):
    query = "super/repo"
    with app.test_client() as client:
        response = client.post(
            "/search",
            data={"query": query},
            follow_redirects=True,
            content_type="application/x-www-form-urlencoded",
        )
        assert response.status_code == 200
        assert "feb3a2837630c0e51447fc1d7e68d86f964a8440".encode("utf-8") in response.data


def test_search_by_email_single_match(sql_engine):
    query = "mini@me"
    with app.test_client() as client:
        response = client.post(
            "/search",
            data={"query": query},
            follow_redirects=True,
            content_type="application/x-www-form-urlencoded",
        )
        assert response.status_code == 200
        assert "feb3a2837630c0e51447fc1d7e68d86f964a8440".encode("utf-8") in response.data
