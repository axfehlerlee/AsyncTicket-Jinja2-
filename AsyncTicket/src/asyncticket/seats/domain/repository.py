# domain/repository.py	무슨 기능이 필요한지 선언
# - 좌석 등급 정보를 조회하고 저장하는 기능이 필요하다.
# - 도메인 객체와 DB 모델 간의 변환 기능이 필요하다.
# - 저장소 인터페이스를 정의하여 구현체와 도메인 간의 의존성을 분리할 수 있다.
# - 인터페이스를 정의하여 다양한 DB 구현체와 도메인 간의 결합도를 낮출 수 있다.

from abc import ABC, abstractmethod
from asyncticket.seats.domain.seat_info import SeatInfo
from asyncticket.seats.domain.performanc_seat import PerformanceSeat


# 등급 저장소 계약: 등급 조회·저장 기능과 반환할 SeatInfo를 정한다.
# 실제 SQLAlchemy 조회·저장 방법은 인프라 구현체가 담당한다.
class SeatInfoRepository(ABC):
    @abstractmethod
    async def get_seat_info(self, seat_id: int) -> SeatInfo:
        pass

    # ORM 객체 생성 → add → flush → 도메인 객체 반환
    @abstractmethod
    async def save_seat_info(self, seat_info: SeatInfo) -> SeatInfo:
        pass

        # 같은 회차에 같은 이름의 등급이 있는지 확인
    @abstractmethod
    async def grade_exists(self, perf_id: int, name: str) -> bool:
        pass
        # 회차가 존재하면 변경 작업용 잠금을 잡고 True를 반환한다.
    # 회차가 없으면 False를 반환한다.
    @abstractmethod
    async def lock_performance(self, perf_id: int) -> bool:
        pass


# 개별 좌석 저장소 계약: 여러 PerformanceSeat를 저장하는 save_many 기능을 정한다.
# 여기서는 DB 작업이나 commit을 실행하지 않는다.
class PerformanceSeatRepository(ABC):
    @abstractmethod
    async def save_many(self, seats: list[PerformanceSeat]) -> None:
        pass

        # 같은 회차에 요청한 좌석명이 하나라도 이미 있는지 확인
    @abstractmethod
    async def names_exist(
        self, perf_id: int, seat_seqs: list[str]
    ) -> bool:
        pass
