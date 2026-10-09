"""
scai_client/auth.py — Token Manager for SCAI Client
"""
import requests
from datetime import datetime, timedelta
from .exceptions import SCAIAuthError


class TokenManager:
    """Manages JWT access and refresh tokens for the SCAI API."""

    # Refresh token if less than this many seconds remain
    REFRESH_THRESHOLD_SECS = 60

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
        payload = {
            "username": self._username,
            "password": self._password,
        }

        try:
            resp = requests.post(url, json=payload, timeout=self._timeout)
            if resp.status_code != 200:
                raise SCAIAuthError(
                    f"Authentication failed with status {resp.status_code}",
                    status_code=resp.status_code,
                    response_body=resp.json() if resp.content else {}
                )

            data = resp.json()
            self._access_token = data.get("access")
            self._refresh_token = data.get("refresh")
            lifetime_secs = data.get("expires_in", 300)
            self._expires_at = datetime.now() + timedelta(seconds=lifetime_secs)
        except SCAIAuthError:
            raise
        except Exception as exc:
            raise SCAIAuthError(f"Login failed due to network error: {exc}")

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
        payload = {"refresh": self._refresh_token}

        try:
            resp = requests.post(url, json=payload, timeout=self._timeout)
            if resp.status_code == 200:
                data = resp.json()
                self._access_token = data.get("access")
                if "refresh" in data:
                    self._refresh_token = data["refresh"]
                lifetime_secs = data.get("expires_in", 300)
                self._expires_at = datetime.now() + timedelta(seconds=lifetime_secs)
                return
        except Exception:
            pass

        # Fallback to full login if refresh request fails
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
