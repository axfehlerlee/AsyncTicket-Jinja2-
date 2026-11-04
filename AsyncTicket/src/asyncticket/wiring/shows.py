"""공연 서비스의 주입 계약과 실제 객체 조립을 한곳에서 관리한다."""

from typing import Annotated

from fastapi import Depends, FastAPI, Request
from sqlalchemy.ext.asyncio import AsyncSession

from asyncticket.shared.core.database import get_db
from asyncticket.shared.domain.catalog import CatalogPolicy
from asyncticket.shared.infrastructure.catalog import (
    SqlAlchemyCatalogRelations, SqlAlchemyCatalogUnitOfWork,
)
from asyncticket.shows.application.service import ShowApplicationService
from asyncticket.shows.infrastructure.repositories import SqlAlchemyShowRepository

DatabaseSession = Annotated[AsyncSession, Depends(get_db)]


def provide_show_service() -> ShowApplicationService:
    raise NotImplementedError("ShowApplicationService 의존성이 주입되지 않았습니다.")


def get_catalog_policy(request: Request) -> CatalogPolicy:
    return request.app.state.catalog_policy


def create_show_service(
    session: DatabaseSession, policy: Annotated[CatalogPolicy, Depends(get_catalog_policy)],
) -> ShowApplicationService:
    return ShowApplicationService(
        SqlAlchemyShowRepository(session), SqlAlchemyCatalogRelations(session),
        SqlAlchemyCatalogUnitOfWork(session), policy,
    )


def wire_dependencies(app: FastAPI) -> None:
    app.dependency_overrides[provide_show_service] = create_show_service
