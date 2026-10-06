"""
scai_client/config.py — Exercise 4.4
"""
from dataclasses import dataclass


@dataclass
class SCAIClientConfig:
    base_url: str
    username: str
    password: str
    timeout: int = 30
    max_retries: int = 3
    verify_ssl: bool = True

    def __post_init__(self):
        """
        Validate configuration.

        Raises:
            ValueError: if base_url doesn't start with http:// or https://
            ValueError: if timeout <= 0
            ValueError: if username or password is empty
        """
        if not self.base_url.startswith('http://') and not self.base_url.startswith('https://'):
            raise ValueError(
                f"base_url must start with http:// or https://, got: '{self.base_url}'"
            )
        if self.timeout <= 0:
            raise ValueError(f"timeout must be > 0, got: {self.timeout}")
        if not self.username:
            raise ValueError("username must not be empty")
        if not self.password:
            raise ValueError("password must not be empty")
