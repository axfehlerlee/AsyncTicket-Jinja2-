"""회차 응용 서비스가 다른 도메인에 요구하는 최소 계약."""

from typing import Protocol

from asyncticket.shared.domain.catalog import CatalogActor
from asyncticket.shows.domain.show import Show


class ShowAccess(Protocol):
    async def find_by_id(self, show_id: int, *, for_update: bool = False) -> Show: ...

    async def authorize_owner(self, show_id: int, actor: CatalogActor) -> Show:
        """공연 행을 잠그고 소유권을 검사한다. 회차와 같은 요청 DB 세션·트랜잭션을 사용한다.

        반환 전에 commit하지 않으며, 잠금은 회차 변경의 commit/rollback까지 유지한다.
        """
        ...
