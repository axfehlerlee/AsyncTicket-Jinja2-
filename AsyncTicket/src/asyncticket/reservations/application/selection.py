from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from asyncticket.reservations.domain.service import (
    ReservationChecker,
    ReservedPerformanceReader,
    ReservedSeatReader,
)
from asyncticket.shared.core.exceptions import NotFoundException


@dataclass(frozen=True)
class ReservationSelection:
    opens_at: datetime
    closes_at: datetime
    is_open: bool
    seat_price: Decimal | None
    has_active_reservation: bool


class ReservationSelectionReader:
    def __init__(
        self,
        performances: ReservedPerformanceReader,
        seats: ReservedSeatReader,
        reservations: ReservationChecker,
    ) -> None:
        self.performances = performances
        self.seats = seats
        self.reservations = reservations

    async def check(
        self, user_id: int, perf_id: int, perf_seat_id: int
    ) -> ReservationSelection:
        performance = await self.performances.get_reserved_performance(perf_id)
        if performance is None:
            raise NotFoundException("회차를 찾을 수 없습니다.", "PERFORMANCE_NOT_FOUND")

        seat = await self.seats.get_reserved_seat(perf_id, perf_seat_id)
        no_active_reservation = await self.reservations.is_reserv_possible(user_id, perf_id)
        now = datetime.now(timezone.utc)
        return ReservationSelection(
            opens_at=performance.reserv_opens_at,
            closes_at=performance.reserv_closes_at,
            is_open=performance.is_reservation_open(now),
            seat_price=seat.reserved_seat_price if seat else None,
            has_active_reservation=not no_active_reservation,
        )
