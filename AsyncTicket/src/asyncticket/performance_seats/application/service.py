from asyncticket.performance_seats.domain.repository import PerformanceSeatRepository
from asyncticket.performance_seats.domain.performance_seat import PerformanceSeat


from asyncticket.shared.core.exceptions import (
    ConflictException, NotFoundException, SharedException, ValidationException,
)
from asyncticket.performance_seats.domain.repository import SeatLookupConflictError
from asyncticket.shared.core.logger import get_logger

logger = get_logger(__name__)


class SeatReservationConflictError(ConflictException):
    """기존 호출자가 구분하는 예외 이름을 유지하며 팀 공통 409 처리에 연결한다."""
    def __init__(self, message: str):
        super().__init__(message, error_code="SEAT_RESERVATION_CONFLICT")


class PerformanceSeatService:
    def __init__(self, repository: PerformanceSeatRepository):
        self.repository = repository

    async def list_performance_seats(self, perf_id: int) -> list[PerformanceSeat]:
        # 회차가 없는 경우와 회차는 있지만 좌석이 없는 경우를 구분한다.
        if not await self.repository.performance_exists(perf_id):
            raise NotFoundException("공연 회차가 없습니다.", error_code="PERFORMANCE_NOT_FOUND")
        return await self.repository.list_performance_seats(perf_id)

    async def get_performance_seat(
        self, perf_id: int, seat_seq: str
    ) -> PerformanceSeat:
        if not await self.repository.performance_exists(perf_id):
            raise NotFoundException("공연 회차가 없습니다.", error_code="PERFORMANCE_NOT_FOUND")

        try:
            seat = await self.repository.get_performance_seat(perf_id, seat_seq)
        except SeatLookupConflictError as exc:
            # 좌석 식별 중복은 데이터 정합성 오류다. 임의의 한 좌석을 반환하지 않는다.
            logger.error("회차 %s의 좌석명이 중복됩니다: %s", perf_id, seat_seq)
            raise SharedException(
                "좌석 정보를 확인할 수 없습니다.", status_code=500,
                error_code="SEAT_LOOKUP_INTEGRITY_ERROR",
            ) from exc
        if seat is None:
            raise NotFoundException("해당 회차에 좌석이 없습니다.", error_code="SEAT_NOT_FOUND")
        return seat

    async def assign_reservation(
        self, *, perf_id: int, perf_seat_id: int, reserv_id: int,
        expected_status: str, reserved_status: str,
    ) -> None:
        """예매와 같은 세션에서 호출한다. 상태값은 팀 합의 후 전달한다."""
        if min(perf_id, perf_seat_id, reserv_id) <= 0:
            raise ValidationException("회차·좌석·예매 번호는 양수여야 합니다.", error_code="INVALID_SEAT_RESERVATION_ID")
        if not expected_status or not reserved_status or expected_status == reserved_status:
            raise ValidationException("연결 전후의 서로 다른 좌석 상태가 필요합니다.", error_code="INVALID_SEAT_STATUS_TRANSITION")
        linked = await self.repository.assign_reservation(
            perf_id=perf_id, perf_seat_id=perf_seat_id, reserv_id=reserv_id,
            expected_status=expected_status, reserved_status=reserved_status,
        )
        if not linked:
            raise SeatReservationConflictError("좌석을 예매에 연결할 수 없습니다.")
