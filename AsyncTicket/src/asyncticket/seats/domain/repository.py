"""좌석 등급을 읽는 데 필요한 계약. DB 구현은 infrastructure가 맡는다."""

from abc import ABC, abstractmethod

from asyncticket.seats.domain.seat_info import SeatInfo


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
