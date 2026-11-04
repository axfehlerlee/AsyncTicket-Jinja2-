"""공연·회차의 저장소·정책·트랜잭션을 같은 요청 세션으로 조립한다."""

from typing import Annotated

from fastapi import Depends, FastAPI, Request
from sqlalchemy.ext.asyncio import AsyncSession

from asyncticket.performances.application.service import PerformanceApplicationService
from asyncticket.performances.infrastructure.repositories import SqlAlchemyPerformanceRepository
from asyncticket.performances.presentation.dependencies import provide_performance_service
from asyncticket.shared.core.database import get_db
from asyncticket.shared.domain.catalog import CatalogPolicy
from asyncticket.shared.infrastructure.catalog import (
    SqlAlchemyCatalogRelations, SqlAlchemyCatalogUnitOfWork,
)
from asyncticket.shows.application.service import ShowApplicationService
from asyncticket.shows.infrastructure.repositories import SqlAlchemyShowRepository
from asyncticket.shows.presentation.dependencies import provide_show_service

DatabaseSession = Annotated[AsyncSession, Depends(get_db)]


def get_catalog_policy(request: Request) -> CatalogPolicy:
    return request.app.state.catalog_policy


def create_show_service(
    session: DatabaseSession, policy: Annotated[CatalogPolicy, Depends(get_catalog_policy)],
) -> ShowApplicationService:
    return ShowApplicationService(
        SqlAlchemyShowRepository(session), SqlAlchemyCatalogRelations(session),
        SqlAlchemyCatalogUnitOfWork(session), policy,
    )


def create_performance_service(
    session: DatabaseSession,
    show_service: Annotated[ShowApplicationService, Depends(provide_show_service)],
    policy: Annotated[CatalogPolicy, Depends(get_catalog_policy)],
) -> PerformanceApplicationService:
    # Depends(get_db)의 요청 단위 캐시로 소유권 확인과 회차 쓰기가 같은 세션을 쓴다.
    return PerformanceApplicationService(
        SqlAlchemyPerformanceRepository(session), show_service,
        SqlAlchemyCatalogRelations(session), SqlAlchemyCatalogUnitOfWork(session), policy,
    )


def wire_dependencies(app: FastAPI) -> None:
    app.dependency_overrides.update({
        provide_show_service: create_show_service,
        provide_performance_service: create_performance_service,
    })
