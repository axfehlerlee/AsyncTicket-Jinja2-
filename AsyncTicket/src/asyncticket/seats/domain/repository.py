from abc import ABC, abstractmethod

from asyncticket.seats.domain.performanc_seat import PerformanceSeat
from asyncticket.seats.domain.seat_info import SeatInfo


class SeatLookupConflictError(Exception):
    pass


class SeatInfoRepository(ABC):
    @abstractmethod
    async def get_seat_info(self, seat_id: int) -> SeatInfo | None:
        pass

    @abstractmethod
    async def get_seat_info_view(self, perf_id: int, seat_id: int) -> dict[str, object] | None:
        pass

    @abstractmethod
    async def save_seat_info(self, seat_info: SeatInfo) -> SeatInfo:
        pass

    @abstractmethod
    async def grade_exists(self, perf_id: int, name: str) -> bool:
        pass

    @abstractmethod
    async def lock_performance(self, perf_id: int) -> bool:
        pass

    @abstractmethod
    async def performance_exists(self, perf_id: int) -> bool:
        pass

    @abstractmethod
    async def get_management_context(self, perf_id: int) -> dict[str, object] | None:
        pass

    @abstractmethod
    async def commit(self) -> None:
        pass

    @abstractmethod
    async def rollback(self) -> None:
        pass


class PerformanceSeatRepository(ABC):
    @abstractmethod
    async def save_many(self, seats: list[PerformanceSeat]) -> None:
        pass

    @abstractmethod
    async def names_exist(self, perf_id: int, seat_seqs: list[str]) -> bool:
        pass

    @abstractmethod
    async def list_performance_seats(self, perf_id: int) -> list[dict[str, object]]:
        pass

    @abstractmethod
    async def get_performance_seat(self, perf_id: int, seat_seq: str) -> dict[str, object] | None:
        pass

    @abstractmethod
    async def get_owned_reservation_seats(
        self, reserv_id: int, user_id: int,
    ) -> dict[str, object] | None:
        pass
