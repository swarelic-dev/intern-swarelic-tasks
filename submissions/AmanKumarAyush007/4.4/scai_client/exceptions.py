"""Explicit error taxonomy for upstream client consumers."""
from __future__ import annotations
from typing import Any


class SCAIAPIError(Exception):
    """Base error for a failed request to SCAI."""

    def __init__(self, message: str, status_code: int | None = None,
                 response_body: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class SCAIAuthError(SCAIAPIError):
    """Credentials or permissions were rejected by the API."""


class SCAINotFoundError(SCAIAPIError):
    """The requested resource was not found."""


class SCAIValidationError(SCAIAPIError):
    """The API rejected a JSON payload with validation errors."""

    def __init__(self, message: str, errors: dict[str, Any]) -> None:
        super().__init__(message, 400, errors)
        self.errors = errors
