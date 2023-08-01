"""Test healtz endpoint."""


def test_health(app):
    """test health endpoint."""
    response = app.get("/healthz")
    assert response.status_code == 200


def test_docs(app):
    """test docs endpoints."""
    response = app.get("/api")
    assert response.status_code == 200

    response = app.get("/api.html")
    assert response.status_code == 200
