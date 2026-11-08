from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from asyncticket.reservations.application.selection import ReservationSelectionReader
from asyncticket.reservations.infrastructure.services import (
    SqlAlchemyReservationChecker,
    SqlAlchemyReservedPerformanceReader,
    SqlAlchemyReservedSeatReader,
)
from asyncticket.shared.core.database import get_db


def get_reservation_selection_reader(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ReservationSelectionReader:
    return ReservationSelectionReader(
        SqlAlchemyReservedPerformanceReader(session),
        SqlAlchemyReservedSeatReader(session),
        SqlAlchemyReservationChecker(session),
    )
