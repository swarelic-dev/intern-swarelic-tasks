"""
scai_client/client.py — SCAI REST API Client Implementation for Exercise 4.4
"""
import requests
from .config import SCAIClientConfig
from .auth import TokenManager
from .exceptions import SCAIAPIError, SCAIAuthError, SCAINotFoundError, SCAIValidationError


class SCAIClient:
    """
    Python client for the Swarelic SCAI REST API.

    Usage:
        config = SCAIClientConfig(
            base_url='http://localhost:8000',
            username='alice',
            password='secret'
        )
        client = SCAIClient(config)
        logs = client.list_call_logs(status='completed')
    """

    def __init__(self, config: SCAIClientConfig):
        self._config = config
        self._token_manager = TokenManager(
            base_url=config.base_url,
            username=config.username,
            password=config.password,
            timeout=config.timeout,
        )
        self._session = requests.Session()
        self._session.verify = config.verify_ssl

    def _request(self, method: str, path: str, **kwargs) -> dict | None:
        """
        Make an authenticated HTTP request to the SCAI API.

        Handles:
        - Automatic Authorization header injection
        - Token refresh on 401 (retry once)
        - 404 → SCAINotFoundError
        - 400 → SCAIValidationError
        - Other 4xx/5xx → SCAIAPIError

        Args:
            method: HTTP method ('GET', 'POST', 'PATCH', 'DELETE')
            path: API path, e.g. '/api/v1/call-logs/'
            **kwargs: passed to requests.Session.request()

        Returns:
            Parsed JSON dict, or None for 204 No Content.
        """
        url = f"{self._config.base_url.rstrip('/')}{path}"
        headers = kwargs.pop('headers', {})

        token = self._token_manager.get_access_token()
        headers['Authorization'] = f"Bearer {token}"

        resp = self._session.request(
            method=method,
            url=url,
            headers=headers,
            timeout=self._config.timeout,
            **kwargs
        )

        # Retry once on 401 Unauthorized
        if resp.status_code == 401:
            self._token_manager.invalidate()
            token = self._token_manager.get_access_token()
            headers['Authorization'] = f"Bearer {token}"
            resp = self._session.request(
                method=method,
                url=url,
                headers=headers,
                timeout=self._config.timeout,
                **kwargs
            )

        if resp.status_code == 204:
            return None

        if resp.status_code == 404:
            body = resp.json() if resp.content else {}
            raise SCAINotFoundError(f"Resource not found: {path}", status_code=404, response_body=body)

        if resp.status_code == 400:
            body = resp.json() if resp.content else {}
            raise SCAIValidationError(f"Validation error: {path}", errors=body)

        if resp.status_code in (401, 403):
            body = resp.json() if resp.content else {}
            raise SCAIAuthError(f"Authentication failure: {path}", status_code=resp.status_code, response_body=body)

        if resp.status_code >= 400:
            body = resp.json() if resp.content else {}
            raise SCAIAPIError(f"HTTP error {resp.status_code}: {resp.text}", status_code=resp.status_code, response_body=body)

        return resp.json() if resp.content else {}

    # ── Call Logs ────────────────────────────────────────────────

    def list_call_logs(self, status: str = None, page: int = 1,
                       page_size: int = 20, search: str = None) -> dict:
        """
        GET /api/v1/call-logs/
        Returns paginated response: {count, next, previous, results}
        """
        params = {}
        if status is not None:
            params['status'] = status
        if page is not None and page != 1:
            params['page'] = page
        if page_size is not None and page_size != 20:
            params['page_size'] = page_size
        if search is not None:
            params['search'] = search

        return self._request('GET', '/api/v1/call-logs/', params=params)

    def get_call_log(self, call_id: int) -> dict:
        """GET /api/v1/call-logs/{id}/"""
        return self._request('GET', f'/api/v1/call-logs/{call_id}/')

    def create_call_log(self, agent_name: str, caller_number: str,
                        duration_secs: int, status: str, notes: str = '') -> dict:
        """POST /api/v1/call-logs/ — Returns the created call log dict."""
        data = {
            'agent_name': agent_name,
            'caller_number': caller_number,
            'duration_secs': duration_secs,
            'status': status,
            'notes': notes,
        }
        return self._request('POST', '/api/v1/call-logs/', json=data)

    def update_call_log(self, call_id: int, **fields) -> dict:
        """PATCH /api/v1/call-logs/{id}/ — Partial update."""
        return self._request('PATCH', f'/api/v1/call-logs/{call_id}/', json=fields)

    def delete_call_log(self, call_id: int) -> None:
        """DELETE /api/v1/call-logs/{id}/ — Returns None on success."""
        return self._request('DELETE', f'/api/v1/call-logs/{call_id}/')
