"""Test healtz endpoint."""


def test_health(app):
    """test health endpoint."""
    response = app.get("/healthz")
    assert response.status_code == 200
