from typing import Annotated, Any, Callable

from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from asyncticket.seats.application.service import SeatService
from asyncticket.seats.domain.repository import PerformanceSeatRepository
from asyncticket.seats.infrastructure.repositories import SqlAlchemySeatRepository
from asyncticket.seats.presentation.dependencies import provide_seat_service


def wire_dependencies(
    app: FastAPI, db_dependency: Callable[..., Any] | None = None
) -> None:
    """공통 앱에서 호출한다. 테스트에서는 별도 DB 세션을 전달할 수 있다.

    공통 main.py에서 app 생성 후 wire_dependencies(app)를 호출하고,
    seats.presentation.router의 router를 app.include_router(router)로 등록한다.
    """
    if db_dependency is None:
        # 공용 DB 설정 전에도 라우터·서비스 코드를 따로 검사할 수 있게 늦게 읽는다.
        from asyncticket.shared.core.database import get_db

        db_dependency = get_db

    def create_seat_repository(
        session: Annotated[AsyncSession, Depends(db_dependency)],
    ) -> PerformanceSeatRepository:
        return SqlAlchemySeatRepository(session)

    def create_seat_service(
        repository: Annotated[
            PerformanceSeatRepository, Depends(create_seat_repository)
        ],
    ) -> SeatService:
        return SeatService(repository)

    app.dependency_overrides[provide_seat_service] = create_seat_service
