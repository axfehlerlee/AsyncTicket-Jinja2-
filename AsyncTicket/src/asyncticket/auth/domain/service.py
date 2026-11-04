from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from asyncticket.users.domain.users import UserRole


@dataclass(frozen=True)
class AccessTokenPayload:
    access_token: str
    user_id: int
    role: UserRole
    jti: str
    expires_at: datetime


class TokenProvider(Protocol):
    def issue_access_token(
        self,
        user_id: int,
        role: UserRole,
    ) -> AccessTokenPayload:
        ...

    def verify_access_token(
        self,
        token: str,
    ) -> AccessTokenPayload:
        ...