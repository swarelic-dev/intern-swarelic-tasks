"""Validated client configuration; secrets are never loaded implicitly."""
from __future__ import annotations
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class SCAIClientConfig:
    """Connection, authentication, and resilience settings."""
    base_url: str
    username: str
    password: str
    timeout: int = 30
    max_retries: int = 3
    verify_ssl: bool = True

    def __post_init__(self) -> None:
        """Validate configuration before any HTTP requests occur."""
        if not isinstance(self.base_url, str):
            raise ValueError("base_url must be a string")
        parsed = urlsplit(self.base_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("base_url must be an http(s) URL without embedded credentials")
        if any(not isinstance(v, str) or not v.strip() for v in (self.username, self.password)):
            raise ValueError("username and password must be nonempty strings")
        if type(self.timeout) is not int or self.timeout <= 0:
            raise ValueError("timeout must be a positive integer")
        if type(self.max_retries) is not int or self.max_retries < 0:
            raise ValueError("max_retries must be a nonnegative integer")
        if not isinstance(self.verify_ssl, bool):
            raise ValueError("verify_ssl must be boolean")
        object.__setattr__(self, "base_url", self.base_url.rstrip("/"))
