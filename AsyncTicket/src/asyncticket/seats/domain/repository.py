# 도메인 저장소 계약: 필요한 기능과 입력·반환 타입을 정한다.
# 실제 DB 조회·저장은 이 계약을 상속받는 인프라 저장소가 구현한다.

from abc import ABC, abstractmethod
from asyncticket.seats.domain.seat_info import SeatInfo
from asyncticket.seats.domain.performanc_seat import PerformanceSeat


# 좌석 등급의 조회·저장·중복 확인·잠금 계약.
class SeatInfoRepository(ABC):
    # ID에 해당하는 좌석 등급을 반환한다.
    @abstractmethod
    async def get_seat_info(self, seat_id: int) -> SeatInfo:
        pass

    # 등급을 저장하고, 발급된 ID를 담은 등급 객체를 반환한다.
    @abstractmethod
    async def save_seat_info(self, seat_info: SeatInfo) -> SeatInfo:
        pass

    # 같은 회차에 같은 이름의 등급이 있는지 확인한다.
    @abstractmethod
    async def grade_exists(self, perf_id: int, name: str) -> bool:
        pass

    # 회차가 있으면 변경 잠금을 잡고 True, 없으면 False를 반환한다.
    @abstractmethod
    async def lock_performance(self, perf_id: int) -> bool:
        pass


# 개별 좌석의 목록 저장·이름 중복 확인 계약.
class PerformanceSeatRepository(ABC):
    # 전달받은 개별 좌석 목록을 저장한다.
    @abstractmethod
    async def save_many(self, seats: list[PerformanceSeat]) -> None:
        pass

    # 같은 회차에 요청한 좌석명이 하나라도 이미 있는지 확인한다.
    @abstractmethod
    async def names_exist(
        self, perf_id: int, seat_seqs: list[str]
    ) -> bool:
        pass
