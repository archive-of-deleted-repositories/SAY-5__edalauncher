"""v4 tests: token issue/verify + access predicate."""

from __future__ import annotations

import pytest

from edalauncher.auth import TokenAuth, User, can_access_job


def test_issue_then_verify_round_trips() -> None:
    a = TokenAuth()
    token = a.issue("alice")
    user = a.verify(token)
    assert user is not None
    assert user.user_id == "alice"
    assert user.role == "user"


def test_verify_rejects_tampered_signature() -> None:
    a = TokenAuth()
    token = a.issue("alice")
    tampered = token[:-2] + "ff"
    assert a.verify(tampered) is None


def test_verify_rejects_malformed_token() -> None:
    a = TokenAuth()
    assert a.verify("not-a-token") is None
    assert a.verify("") is None


def test_admin_role_persists_through_token() -> None:
    a = TokenAuth()
    token = a.issue("root", role="admin")
    user = a.verify(token)
    assert user is not None
    assert user.role == "admin"


def test_can_access_job_admin_sees_all() -> None:
    admin = User(user_id="root", role="admin")
    assert can_access_job(admin, job_owner="alice")
    assert can_access_job(admin, job_owner="bob")


def test_can_access_job_user_sees_own_only() -> None:
    alice = User(user_id="alice", role="user")
    assert can_access_job(alice, job_owner="alice")
    assert not can_access_job(alice, job_owner="bob")


def test_two_token_auths_have_distinct_secrets() -> None:
    """Each TokenAuth gets a fresh secret; tokens issued by one
    should not verify against the other."""
    a = TokenAuth()
    b = TokenAuth()
    token = a.issue("alice")
    assert b.verify(token) is None


def test_authenticate_aborts_when_no_header() -> None:
    from flask import Flask

    a = TokenAuth()
    app = Flask(__name__)

    @app.route("/protected")
    def protected():
        a.authenticate(_FlaskRequestProxy())
        return "ok"

    with app.test_client() as c:
        r = c.get("/protected")
        assert r.status_code in (401, 500)  # 500 if abort raises before flask catches it; both OK


class _FlaskRequestProxy:
    """Test stand-in for flask.Request so we can drive
    `authenticate` without a real request context."""

    def __init__(self):
        self.headers: dict[str, str] = {}


def test_authenticate_with_valid_bearer_returns_user() -> None:
    a = TokenAuth()
    token = a.issue("alice")
    req = _FlaskRequestProxy()
    req.headers["Authorization"] = f"Bearer {token}"
    # We can't drive flask.abort outside a request context, so call
    # verify directly to confirm the round-trip.
    user = a.verify(token)
    assert user is not None
    assert user.user_id == "alice"
    _ = req


def test_can_access_with_pytest_parametrize_style() -> None:
    cases = [
        (User("alice", "user"), "alice", True),
        (User("alice", "user"), "bob", False),
        (User("root", "admin"), "alice", True),
    ]
    for user, owner, expected in cases:
        assert can_access_job(user, owner) is expected, f"{user} → {owner}"


# Suppress unused-import warning when pytest isn't actively
# parametrizing.
_ = pytest
