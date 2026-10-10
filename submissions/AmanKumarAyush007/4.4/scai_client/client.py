"""Connection-reusing client with safe retries and explicit error mappings."""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlsplit

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .auth import TokenManager
from .config import SCAIClientConfig
from .exceptions import SCAIAPIError, SCAIAuthError, SCAINotFoundError, SCAIValidationError

logger = logging.getLogger(__name__)


class SCAIClient:
    """Authenticated interface to the versioned SCAI call-log API."""

    def __init__(self, config: SCAIClientConfig) -> None:
        self._config = config
        self._session = requests.Session()
        # Do not replay mutating requests automatically; retries are limited to idempotent methods.
        retry = Retry(total=config.max_retries, backoff_factor=0.3,
                      status_forcelist=(429, 502, 503, 504), allowed_methods=frozenset({"GET", "HEAD"}))
        adapter = HTTPAdapter(max_retries=retry)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)
        self._token_manager = TokenManager(config.base_url, config.username, config.password,
                                           config.timeout, session=self._session, verify_ssl=config.verify_ssl)

    def close(self) -> None:
        """Close underlying HTTP connections."""
        self._session.close()

    def __enter__(self) -> "SCAIClient":
        return self

    def __exit__(self, *_args: Any) -> None:
        self.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Call an authenticated endpoint and translate response failures."""
        if not path.startswith("/") or path.startswith("//") or urlsplit(path).netloc:
            raise ValueError("path must be a relative absolute-path reference")
        url = self._config.base_url + path
        headers = dict(kwargs.pop("headers", {}) or {})
        headers.pop("Authorization", None)
        for attempt in range(2):
            token = self._token_manager.get_access_token()
            headers["Authorization"] = f"Bearer {token}"
            try:
                response = self._session.request(method, url, headers=headers,
                                                 timeout=self._config.timeout, verify=self._config.verify_ssl, **kwargs)
            except requests.RequestException as exc:
                raise SCAIAPIError("SCAI endpoint is unavailable") from exc
            if response.status_code == 401 and attempt == 0:
                self._token_manager.invalidate()
                continue
            return self._handle_response(response)
        raise SCAIAuthError("Authentication failed after token renewal", 401)

    @staticmethod
    def _handle_response(response: requests.Response) -> dict[str, Any]:
        """Decode successful JSON and normalize API errors."""
        if response.status_code == 204 or not response.content:
            if response.ok:
                return {}
        try:
            parsed = response.json()
        except ValueError:
            parsed = None
        details = parsed if isinstance(parsed, dict) else {}
        if response.status_code in (401, 403):
            raise SCAIAuthError("Authentication or permission denied", response.status_code, details)
        if response.status_code == 404:
            raise SCAINotFoundError("Resource not found", 404, details)
        if response.status_code == 400:
            raise SCAIValidationError("Validation failed", details)
        if not response.ok:
            raise SCAIAPIError(str(details.get("detail", "SCAI request failed")), response.status_code, details)
        if not isinstance(parsed, dict):
            raise SCAIAPIError("Expected a JSON object from SCAI", response.status_code)
        return parsed

    def list_call_logs(self, status: str | None = None, page: int = 1, page_size: int = 20) -> dict:
        """Get paginated call-log records with an optional status filter."""
        if page < 1 or not 1 <= page_size <= 100:
            raise ValueError("page must be >= 1 and page_size must be between 1 and 100")
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if status:
            params["status"] = status
        return self._request("GET", "/api/v1/call-logs/", params=params)

    def get_call_log(self, call_id: int) -> dict:
        """Get a call log by its numeric primary key."""
        return self._request("GET", f"/api/v1/call-logs/{self._validate_id(call_id)}/")

    def create_call_log(self, agent_name: str, caller_number: str, duration_secs: int,
                        status: str, notes: str = "") -> dict:
        """Create a call-log record."""
        if duration_secs < 0:
            raise ValueError("duration_secs cannot be negative")
        return self._request("POST", "/api/v1/call-logs/", json={
            "agent_name": agent_name, "caller_number": caller_number,
            "duration_secs": duration_secs, "status": status, "notes": notes,
        })

    def update_call_log(self, call_id: int, **fields: Any) -> dict:
        """Partially update a call log."""
        if not fields:
            raise ValueError("At least one update field is required")
        return self._request("PATCH", f"/api/v1/call-logs/{self._validate_id(call_id)}/", json=fields)

    def delete_call_log(self, call_id: int) -> None:
        """Delete a call log; a 204 body is intentionally discarded."""
        self._request("DELETE", f"/api/v1/call-logs/{self._validate_id(call_id)}/")
        return None

    @staticmethod
    def _validate_id(value: int) -> int:
        if type(value) is not int or value <= 0:
            raise ValueError("call_id must be a positive integer")
        return value
