"""결제 저장소와 서비스를 요청 세션에 연결한다."""

from typing import Annotated, Any, Callable

from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from asyncticket.payment.application.service import PaymentService
from asyncticket.payment.domain.repository import PaymentRepository
from asyncticket.payment.infrastructure.repositories import SqlAlchemyPaymentRepository
from asyncticket.payment.presentation.dependencies import provider_payment_service


def wire_dependencies(
    app: FastAPI,
    db_dependency: Callable[..., Any] | None = None,
) -> None:
    if db_dependency is None:
        from asyncticket.shared.core.database import get_db

        db_dependency = get_db

    def create_payment_repository(
        session: Annotated[AsyncSession, Depends(db_dependency)],
    ) -> PaymentRepository:
        return SqlAlchemyPaymentRepository(session)

    def create_payment_service(
        repository: Annotated[PaymentRepository, Depends(create_payment_repository)],
    ) -> PaymentService:
        return PaymentService(repository)

    app.dependency_overrides[provider_payment_service] = create_payment_service
