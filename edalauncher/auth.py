"""v4: token-based authentication + multi-user job isolation.

The bare Flask app from v1 has no auth — anyone with the URL can
submit and run jobs. v4 adds a simple bearer-token model:
- Each user is identified by a token (configured via env / file).
- Job submissions tag the job with the requesting user's id.
- /jobs?owner=me returns only jobs owned by the caller.

The crypto is intentionally minimal (HMAC-signed token, not JWT)
because the production deployment fronts EDALauncher with the
team's existing SSO. v4 demonstrates the seam.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass, field

from flask import Request, abort


@dataclass(frozen=True, slots=True)
class User:
    user_id: str
    role: str  # "user" | "admin"


@dataclass
class TokenAuth:
    """In-memory token registry. Production replaces this with a
    DB-backed store + rotation logic."""

    secret: bytes = field(default_factory=lambda: secrets.token_bytes(32))
    users: dict[str, User] = field(default_factory=dict)

    def issue(self, user_id: str, role: str = "user") -> str:
        """Issue a token = HMAC(user_id || role) hex. Server-only —
        the secret never leaves the process."""
        u = User(user_id=user_id, role=role)
        self.users[user_id] = u
        msg = f"{user_id}:{role}".encode()
        sig = hmac.new(self.secret, msg, hashlib.sha256).hexdigest()
        return f"{user_id}.{role}.{sig}"

    def verify(self, token: str) -> User | None:
        try:
            user_id, role, sig = token.split(".", 2)
        except ValueError:
            return None
        msg = f"{user_id}:{role}".encode()
        expected = hmac.new(self.secret, msg, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        return self.users.get(user_id)

    def authenticate(self, request: Request) -> User:
        """Flask helper: extract Bearer token, return User or
        abort(401). Routes that need auth call this first thing."""
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            abort(401)
        token = header.removeprefix("Bearer ").strip()
        user = self.verify(token)
        if user is None:
            abort(401)
        return user


def can_access_job(user: User, job_owner: str) -> bool:
    """Authorization predicate: admins see everything, users see
    only their own jobs."""
    return user.role == "admin" or user.user_id == job_owner
