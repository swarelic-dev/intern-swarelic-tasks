"""
scai_client/client.py — Exercise 4.4

Full implementation of the SCAI REST API client with:
- Auto-login and token refresh
- 401 retry logic
- Typed error mapping (404 → SCAINotFoundError, 400 → SCAIValidationError, etc.)
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
        url = self._config.base_url.rstrip('/') + path

        def _do_request() -> requests.Response:
            token = self._token_manager.get_access_token()
            headers = kwargs.pop('headers', {})
            headers['Authorization'] = f'Bearer {token}'
            return self._session.request(
                method, url,
                headers=headers,
                timeout=self._config.timeout,
                **kwargs,
            )

        resp = _do_request()

        # On 401, invalidate token and retry once
        if resp.status_code == 401:
            self._token_manager.invalidate()
            resp = _do_request()

        return self._handle_response(resp)

    def _handle_response(self, resp: requests.Response) -> dict | None:
        """Map HTTP response to return value or exception."""
        if resp.status_code == 204:
            return None

        if resp.ok:
            return resp.json()

        # Try to parse error body
        try:
            body = resp.json()
        except Exception:
            body = {'detail': resp.text}

        if resp.status_code == 404:
            raise SCAINotFoundError(
                body.get('detail', 'Resource not found'),
                status_code=404,
                response_body=body,
            )
        if resp.status_code == 400:
            raise SCAIValidationError(
                "Validation error",
                errors=body,
            )
        if resp.status_code in (401, 403):
            raise SCAIAuthError(
                body.get('detail', 'Unauthorized'),
                status_code=resp.status_code,
                response_body=body,
            )
        raise SCAIAPIError(
            body.get('detail', f'API error {resp.status_code}'),
            status_code=resp.status_code,
            response_body=body,
        )

    # ── Call Logs ────────────────────────────────────────────────

    def list_call_logs(self, status: str = None, page: int = 1,
                       page_size: int = 20, search: str = None) -> dict:
        """
        GET /api/v1/call-logs/
        Returns paginated response: {count, next, previous, results}
        """
        params = {'page': page, 'page_size': page_size}
        if status is not None:
            params['status'] = status
        if search is not None:
            params['search'] = search
        return self._request('GET', '/api/v1/call-logs/', params=params)

    def get_call_log(self, call_id: int) -> dict:
        """GET /api/v1/call-logs/{id}/"""
        return self._request('GET', f'/api/v1/call-logs/{call_id}/')

    def create_call_log(self, agent_name: str, caller_number: str,
                        duration_secs: int, status: str, notes: str = '') -> dict:
        """POST /api/v1/call-logs/ — Returns the created call log dict."""
        payload = {
            'agent_name': agent_name,
            'caller_number': caller_number,
            'duration_secs': duration_secs,
            'status': status,
            'notes': notes,
        }
        return self._request('POST', '/api/v1/call-logs/', json=payload)

    def update_call_log(self, call_id: int, **fields) -> dict:
        """PATCH /api/v1/call-logs/{id}/ — Partial update."""
        return self._request('PATCH', f'/api/v1/call-logs/{call_id}/', json=fields)

    def delete_call_log(self, call_id: int) -> None:
        """DELETE /api/v1/call-logs/{id}/ — Returns None on success."""
        return self._request('DELETE', f'/api/v1/call-logs/{call_id}/')
