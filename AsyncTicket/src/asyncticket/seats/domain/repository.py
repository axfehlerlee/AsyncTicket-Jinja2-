"""좌석 등급을 읽는 데 필요한 계약. DB 구현은 infrastructure가 맡는다."""

from abc import ABC, abstractmethod

from asyncticket.seats.domain.seat import PerformanceSeat, SeatInfo


class SeatInfoRepository(ABC):
    """상위 계층에 SQLAlchemy 객체가 아닌 SeatInfo를 반환한다."""

    @abstractmethod
    async def get_seat_info(self, seat_id: int) -> SeatInfo | None:
        """등급 설정 한 건을 찾는다. 없으면 None을 반환한다."""
        raise NotImplementedError

    @abstractmethod
    async def list_seat_infos(self, perf_id: int) -> list[SeatInfo]:
        """회차에 속한 등급 설정을 찾는다. 회차 존재 검사는 별도 계약이다."""
        raise NotImplementedError


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
