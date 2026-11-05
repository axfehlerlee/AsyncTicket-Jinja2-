from typing import Annotated, Any, Callable

from fastapi import Depends, FastAPI, Request
from sqlalchemy.ext.asyncio import AsyncSession

from asyncticket.seats.application.service import SeatInfoService
from asyncticket.shared.domain.catalog import CatalogPolicy
from asyncticket.seats.infrastructure.repositories import (
    SqlAlchemyPerformanceSeatRepository,
    SqlAlchemySeatInfoRepository,
)


def provide_seat_info_service() -> SeatInfoService:
    raise RuntimeError("좌석 구성 서비스 연결이 필요합니다.")


def create_seat_info_service(
    session: AsyncSession, policy: CatalogPolicy | None = None,
) -> SeatInfoService:
    """등급 저장소·좌석 저장소·트랜잭션에 같은 세션을 주입한다."""
    return SeatInfoService(
        repository=SqlAlchemySeatInfoRepository(session),
        performance_seat_repository=SqlAlchemyPerformanceSeatRepository(session),
        policy=policy if policy is not None else CatalogPolicy(),
    )


def wire_dependencies(
    app: FastAPI, db_dependency: Callable[..., Any] | None = None,
) -> None:
    if db_dependency is None:
        from asyncticket.shared.core.database import get_db

        db_dependency = get_db

    def seat_info_service(
        request: Request, session: Annotated[AsyncSession, Depends(db_dependency)],
    ) -> SeatInfoService:
        return create_seat_info_service(
            session, getattr(request.app.state, "catalog_policy", CatalogPolicy()),
        )

    app.dependency_overrides.update({
        provide_seat_info_service: seat_info_service,
    })
