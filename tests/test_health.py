"""Test healtz endpoint."""


def test_health(app):
    response = app.get("/healthz")
    assert response.status_code == 200
