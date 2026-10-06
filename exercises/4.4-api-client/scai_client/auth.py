"""
scai_client/auth.py — Exercise 4.4

Implements JWT token management: login, refresh, and expiry handling.
"""
import requests
from datetime import datetime, timedelta
from .exceptions import SCAIAuthError


class TokenManager:
    """Manages JWT access and refresh tokens for the SCAI API."""

    # Refresh token if less than this many seconds remain
    REFRESH_THRESHOLD_SECS = 60

    # Assume access tokens expire in 5 minutes (300s) unless the API tells us otherwise
    DEFAULT_EXPIRY_SECS = 300

    def __init__(self, base_url: str, username: str, password: str, timeout: int):
        self._base_url = base_url.rstrip('/')
        self._username = username
        self._password = password
        self._timeout = timeout
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._expires_at: datetime | None = None

    def get_access_token(self) -> str:
        """
        Return a valid access token.
        - If no token: call _login()
        - If token expires within REFRESH_THRESHOLD_SECS: call _refresh()
        - Otherwise: return cached token

        Raises:
            SCAIAuthError: if login or refresh fails
        """
        if self._access_token is None:
            self._login()
        elif self.is_expired:
            self._refresh()
        return self._access_token

    def _login(self) -> None:
        """
        POST /api/auth/token/ with username+password.
        Store access_token, refresh_token, and compute expires_at.

        Raises:
            SCAIAuthError: on 401 or network error
        """
        url = f"{self._base_url}/api/auth/token/"
        try:
            resp = requests.post(
                url,
                json={'username': self._username, 'password': self._password},
                timeout=self._timeout,
            )
        except requests.RequestException as e:
            raise SCAIAuthError(f"Network error during login: {e}") from e

        if resp.status_code == 401:
            raise SCAIAuthError("Login failed: invalid credentials", status_code=401)
        if not resp.ok:
            raise SCAIAuthError(
                f"Login failed with status {resp.status_code}", status_code=resp.status_code
            )

        data = resp.json()
        self._access_token = data['access']
        self._refresh_token = data.get('refresh')
        # Compute expiry: use 'expires_in' if provided, otherwise default
        expires_in = data.get('expires_in', self.DEFAULT_EXPIRY_SECS)
        self._expires_at = datetime.now() + timedelta(seconds=expires_in)

    def _refresh(self) -> None:
        """
        POST /api/auth/token/refresh/ with the current refresh token.
        If refresh fails (e.g. refresh token expired), fall back to _login().

        Raises:
            SCAIAuthError: if both refresh AND login fail
        """
        if not self._refresh_token:
            self._login()
            return

        url = f"{self._base_url}/api/auth/token/refresh/"
        try:
            resp = requests.post(
                url,
                json={'refresh': self._refresh_token},
                timeout=self._timeout,
            )
        except requests.RequestException:
            # Network error → try full login
            self._login()
            return

        if resp.ok:
            data = resp.json()
            self._access_token = data['access']
            expires_in = data.get('expires_in', self.DEFAULT_EXPIRY_SECS)
            self._expires_at = datetime.now() + timedelta(seconds=expires_in)
        else:
            # Refresh token expired → fall back to full login
            self.invalidate()
            self._login()

    def invalidate(self) -> None:
        """Clear all stored token state."""
        self._access_token = None
        self._refresh_token = None
        self._expires_at = None

    @property
    def is_expired(self) -> bool:
        """True if the access token has expired or is within threshold."""
        if self._expires_at is None:
            return True
        remaining = (self._expires_at - datetime.now()).total_seconds()
        return remaining < self.REFRESH_THRESHOLD_SECS
