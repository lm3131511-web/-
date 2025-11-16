from __future__ import annotations

import os
from typing import Iterable, Set

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


class AuthBackend:
    """Simple bearer-token authenticator."""

    def __init__(self, tokens: Iterable[str] | None = None) -> None:
        self._tokens: Set[str] = {token.strip() for token in tokens or [] if token.strip()}
        self._scheme = HTTPBearer(auto_error=False)

    async def authenticate(self, credentials: HTTPAuthorizationCredentials | None) -> None:
        if not self._tokens:
            return
        if credentials is None or credentials.scheme.lower() != "bearer" or credentials.credentials not in self._tokens:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorised")

    def dependency(self):
        async def _dependency(credentials: HTTPAuthorizationCredentials | None = Depends(self._scheme)):
            await self.authenticate(credentials)
        return _dependency

    async def __call__(self, credentials: HTTPAuthorizationCredentials | None = None) -> None:
        await self.authenticate(credentials)


def build_auth_backend() -> AuthBackend:
    tokens = os.getenv("CODEX_API_TOKENS", "").split(",")
    return AuthBackend(tokens)
