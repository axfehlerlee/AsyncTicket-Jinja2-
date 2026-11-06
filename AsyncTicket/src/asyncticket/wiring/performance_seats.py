from typing import Annotated, Any, Callable

from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from asyncticket.seats.application.service import PerformanceSeatService
from asyncticket.seats.infrastructure.repositories import (
    SqlAlchemyPerformanceSeatRepository, SqlAlchemySeatInfoRepository,
)


def provide_performance_seat_service() -> PerformanceSeatService:
    raise RuntimeError("좌석 조회 서비스 연결이 필요합니다.")


def create_performance_seat_service(session: AsyncSession) -> PerformanceSeatService:
    return PerformanceSeatService(
        SqlAlchemyPerformanceSeatRepository(session), SqlAlchemySeatInfoRepository(session),
    )


def wire_dependencies(
    app: FastAPI, db_dependency: Callable[..., Any] | None = None,
) -> None:
    if db_dependency is None:
        from asyncticket.shared.core.database import get_db

        db_dependency = get_db

    def performance_seat_service(session: Annotated[AsyncSession, Depends(db_dependency)]) -> PerformanceSeatService:
        return create_performance_seat_service(session)

    app.dependency_overrides[provide_performance_seat_service] = performance_seat_service
