"""앱 조립: 같은 요청의 DB 세션·저장소·서비스·트랜잭션을 연결한다."""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from asyncticket.performances.application.service import PerformanceApplicationService
from asyncticket.performances.infrastructure.repositories import SqlAlchemyPerformanceRepository
from asyncticket.shared.core.database import get_db
from asyncticket.shared.domain.catalog import CatalogPolicy
from asyncticket.shared.infrastructure.catalog import (
    SqlAlchemyCatalogRelations, SqlAlchemyCatalogUnitOfWork,
)
from asyncticket.shows.application.service import ShowApplicationService
from asyncticket.shows.infrastructure.repositories import SqlAlchemyShowRepository


from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)


DatabaseSession = Annotated[AsyncSession, Depends(get_db)]


def get_catalog_policy(request: Request) -> CatalogPolicy:
    return request.app.state.catalog_policy


def get_show_service(
    session: DatabaseSession, policy: Annotated[CatalogPolicy, Depends(get_catalog_policy)],
) -> ShowApplicationService:
    return ShowApplicationService(
        SqlAlchemyShowRepository(session), SqlAlchemyCatalogRelations(session),
        SqlAlchemyCatalogUnitOfWork(session), policy,
    )


def get_performance_service(
    session: DatabaseSession,
    show_service: Annotated[ShowApplicationService, Depends(get_show_service)],
    policy: Annotated[CatalogPolicy, Depends(get_catalog_policy)],
) -> PerformanceApplicationService:
    # 공연 소유권 확인과 회차 쓰기가 같은 세션/트랜잭션에서 실행된다.
    return PerformanceApplicationService(
        SqlAlchemyPerformanceRepository(session), show_service,
        SqlAlchemyCatalogRelations(session), SqlAlchemyCatalogUnitOfWork(session), policy,
    )


