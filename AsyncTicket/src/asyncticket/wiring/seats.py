from typing import Annotated, Any, Callable

from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from asyncticket.seats.application.service import SeatInfoService
from asyncticket.seats.domain.repository import SeatInfoRepository
from asyncticket.seats.infrastructure.repositories import SqlAlchemySeatInfoRepository
from asyncticket.seats.presentation.dependencies import provide_seat_info_service


def wire_dependencies(
    app: FastAPI, db_dependency: Callable[..., Any] | None = None
) -> None:
    """좌석 등급 저장소와 서비스를 연결한다."""
    if db_dependency is None:
        # 공용 DB 설정 전에도 라우터·서비스 코드를 따로 검사할 수 있게 늦게 읽는다.
        from asyncticket.shared.core.database import get_db

        db_dependency = get_db

    def create_seat_repository(
        session: Annotated[AsyncSession, Depends(db_dependency)],
    ) -> SeatInfoRepository:
        return SqlAlchemySeatInfoRepository(session)

    def create_seat_service(
        repository: Annotated[
            SeatInfoRepository, Depends(create_seat_repository)
        ],
    ) -> SeatInfoService:
        return SeatInfoService(repository)

    app.dependency_overrides[provide_seat_info_service] = create_seat_service
