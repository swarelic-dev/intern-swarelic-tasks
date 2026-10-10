"""JWT login, refresh, expiry and token invalidation."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from threading import RLock

import requests

from .exceptions import SCAIAuthError

logger = logging.getLogger(__name__)
REFRESH_THRESHOLD_SECS = 60


class TokenManager:
    """Cache short-lived access tokens, refreshing before expiration."""

    def __init__(self, base_url: str, username: str, password: str, timeout: int,
                 session: requests.Session | None = None, verify_ssl: bool = True) -> None:
        self._base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._timeout = timeout
        self._session = session if session is not None else requests.Session()
        self._verify_ssl = verify_ssl
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._expires_at: datetime | None = None
        self._lock = RLock()

    def get_access_token(self) -> str:
        """Get a token; log in or refresh as needed under an in-process lock."""
        with self._lock:
            now = datetime.now(timezone.utc)
            if self._access_token and self._expires_at and self._expires_at - now > timedelta(seconds=REFRESH_THRESHOLD_SECS):
                return self._access_token
            if self._refresh_token:
                self._refresh()
            else:
                self._login()
            if not self._access_token:
                raise SCAIAuthError("Authentication did not provide an access token")
            return self._access_token

    def _post_token(self, path: str, body: dict[str, str]) -> dict:
        try:
            response = self._session.post(self._base_url + path, json=body,
                                          timeout=self._timeout, verify=self._verify_ssl)
        except requests.RequestException as exc:
            raise SCAIAuthError("Could not contact authentication endpoint") from exc
        if not response.ok:
            raise SCAIAuthError("Authentication endpoint rejected credentials", response.status_code)
        try:
            payload = response.json()
        except ValueError as exc:
            raise SCAIAuthError("Authentication endpoint returned invalid JSON") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("access"), str) or not payload["access"]:
            raise SCAIAuthError("Missing access token in authentication response")
        return payload

    def _save(self, payload: dict) -> None:
        self._access_token = payload["access"]
        if isinstance(payload.get("refresh"), str):
            self._refresh_token = payload["refresh"]
        # The SCAI exercise assumes expiry metadata; default conservatively when absent.
        raw_lifetime = payload.get("expires_in", 300)
        lifetime = raw_lifetime if type(raw_lifetime) in (int, float) and raw_lifetime > 0 else 300
        self._expires_at = datetime.now(timezone.utc) + timedelta(seconds=lifetime)

    def _login(self) -> None:
        """POST /api/auth/token/ and cache the response."""
        self._save(self._post_token("/api/auth/token/", {"username": self._username, "password": self._password}))

    def _refresh(self) -> None:
        """Refresh cached credentials; fall back to login on failure."""
        if not self._refresh_token:
            self._login()
            return
        try:
            self._save(self._post_token("/api/auth/token/refresh/", {"refresh": self._refresh_token}))
        except SCAIAuthError:
            logger.info("Token refresh rejected; starting new login")
            self.invalidate()
            self._login()

    def invalidate(self) -> None:
        """Discard authentication state, e.g. after a 401 response."""
        with self._lock:
            self._access_token = None
            self._refresh_token = None
            self._expires_at = None
