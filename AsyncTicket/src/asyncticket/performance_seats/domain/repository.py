"""회차별 개별 좌석 저장소 계약."""
from abc import ABC, abstractmethod
from asyncticket.performance_seats.domain.performance_seat import PerformanceSeat


class SeatLookupConflictError(Exception):
    """같은 회차에서 좌석명을 하나로 식별할 수 없는 경우."""


class PerformanceSeatRepository(ABC):
    @abstractmethod
    async def performance_exists(self, perf_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def list_performance_seats(self, perf_id: int) -> list[PerformanceSeat]:
        raise NotImplementedError

    @abstractmethod
    async def get_performance_seat(
        self, perf_id: int, seat_seq: str
    ) -> PerformanceSeat | None:
        raise NotImplementedError

    @abstractmethod
    async def assign_reservation(
        self, *, perf_id: int, perf_seat_id: int, reserv_id: int,
        expected_status: str, reserved_status: str,
    ) -> bool:
        """같은 회차의 예매를 미연결 좌석에 연결한다. commit은 호출자가 맡는다."""
        raise NotImplementedError
