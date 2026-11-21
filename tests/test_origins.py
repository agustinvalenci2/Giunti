import pytest

from backend.config import Settings


REGISTRATION = {
    "username": "origin_test",
    "email": "origin@example.com",
    "password": "Origin-regression-423!",
}


@pytest.fixture
def vercel_origins(monkeypatch, settings):
    monkeypatch.setenv("APP_ORIGINS", " https://cuaderno.example/ , https://www.cuaderno.example ")
    monkeypatch.setenv("VERCEL_URL", "cuaderno-abc123-team.vercel.app")
    monkeypatch.setenv("VERCEL_BRANCH_URL", "cuaderno-git-main-team.vercel.app")
    monkeypatch.setenv("VERCEL_PROJECT_PRODUCTION_URL", "cuaderno.vercel.app")
    monkeypatch.setattr(settings, "allowed_origins", Settings().allowed_origins)


@pytest.mark.parametrize("origin", [
    "https://cuaderno-abc123-team.vercel.app",
    "https://cuaderno-git-main-team.vercel.app",
    "https://cuaderno.vercel.app",
    "https://cuaderno.example",
    "https://www.cuaderno.example",
])
def test_project_origin_allows_registration_behind_proxy(client, vercel_origins, origin):
    response = client.post("/api/auth/register", json=REGISTRATION, headers={
        "Origin": origin,
        "Sec-Fetch-Site": "same-origin",
        "Host": "internal-container:80",
        "X-Forwarded-Proto": "https",
    })
    assert response.status_code == 201
    assert response.json()["user"]["username"] == REGISTRATION["username"]


@pytest.mark.parametrize("origin", [
    "https://other-project.vercel.app",
    "https://cuaderno.vercel.app.evil.example",
    "http://cuaderno.vercel.app",
    "null",
])
def test_other_origins_cannot_bypass_allowlist_with_headers(client, vercel_origins, origin):
    response = client.post("/api/auth/register", json=REGISTRATION, headers={
        "Origin": origin,
        "Sec-Fetch-Site": "same-origin",
        "Host": origin.removeprefix("https://"),
        "X-Forwarded-Host": origin.removeprefix("https://"),
        "X-Forwarded-Proto": "https",
    })
    assert response.status_code == 403
    assert response.json()["detail"] == "Origen no permitido."


def test_trusted_origin_still_requires_csrf(client, vercel_origins):
    client.headers.update({"Origin": "https://cuaderno.vercel.app", "Sec-Fetch-Site": "same-origin"})
    registration = client.post("/api/auth/register", json=REGISTRATION)
    assert registration.status_code == 201
    assert client.post("/api/auth/logout").status_code == 403
    assert client.post("/api/auth/logout", headers={"X-CSRF-Token": registration.json()["csrf_token"]}).status_code == 204


def test_local_origin_still_works_without_vercel(client, monkeypatch, settings):
    for name in ("APP_ORIGINS", "VERCEL_URL", "VERCEL_BRANCH_URL", "VERCEL_PROJECT_PRODUCTION_URL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(settings, "allowed_origins", Settings().allowed_origins)
    response = client.post("/api/auth/register", json=REGISTRATION, headers={
        "Origin": "http://localhost:5173", "Sec-Fetch-Site": "same-origin",
    })
    assert response.status_code == 201
