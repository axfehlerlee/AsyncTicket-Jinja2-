"""회차 서비스와 공연 서비스가 같은 요청 DB 세션을 사용하도록 조립한다."""

from typing import Annotated

from fastapi import Depends, FastAPI

from asyncticket.performances.application.ports import ShowAccess
from asyncticket.performances.application.service import PerformanceApplicationService
from asyncticket.performances.infrastructure.repositories import SqlAlchemyPerformanceRepository
from asyncticket.shared.domain.catalog import CatalogPolicy
from asyncticket.shared.infrastructure.catalog import (
    SqlAlchemyCatalogRelations, SqlAlchemyCatalogUnitOfWork,
)
from asyncticket.wiring.common import DatabaseSession, get_catalog_policy
from asyncticket.wiring.shows import provide_show_service


def provide_performance_service() -> PerformanceApplicationService:
    raise NotImplementedError("PerformanceApplicationService 의존성이 주입되지 않았습니다.")


def create_performance_service(
    session: DatabaseSession,
    show_service: Annotated[ShowAccess, Depends(provide_show_service)],
    policy: Annotated[CatalogPolicy, Depends(get_catalog_policy)],
) -> PerformanceApplicationService:
    # Depends(get_db)의 요청 단위 캐시로 소유권 확인과 회차 쓰기가 같은 세션을 쓴다.
    return PerformanceApplicationService(
        SqlAlchemyPerformanceRepository(session), show_service,
        SqlAlchemyCatalogRelations(session), SqlAlchemyCatalogUnitOfWork(session), policy,
    )


def wire_dependencies(app: FastAPI) -> None:
    app.dependency_overrides[provide_performance_service] = create_performance_service
