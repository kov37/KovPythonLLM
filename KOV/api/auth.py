"""Local bearer token creation and constant-time validation."""

from __future__ import annotations

import hmac
import os
import secrets
from pathlib import Path


class LocalTokenAuth:
    def __init__(self, token_path: Path) -> None:
        self.token_path = token_path

    def initialize(self) -> str:
        self.token_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not self.token_path.exists():
            temporary = self.token_path.with_suffix(".tmp")
            temporary.write_text(secrets.token_urlsafe(32), encoding="utf-8")
            os.chmod(temporary, 0o600)
            os.replace(temporary, self.token_path)
        os.chmod(self.token_path, 0o600)
        return self.token_path.read_text(encoding="utf-8").strip()

    def verify(self, authorization: str | None) -> bool:
        if not authorization or not authorization.startswith("Bearer "):
            return False
        return hmac.compare_digest(authorization[7:], self.initialize())
