"""
예매 저장소 약속
    1) 예매를 저장 (예매생성은 reservation.py (Reservation에서))
    2) 예매 ID로 찾고
    3) 회원의 예매 목록을 찾고
    4) 바뀐 상태를 저장
"""

from abc import ABC, abstractmethod
from asyncticket.reservations.domain.reservation import Reservation


class ReservationRepository(ABC):

    @abstractmethod
    async def add(self, reservation:Reservation) -> Reservation:
        """1) 예매 저장후 reserv_id가 채워진 예매를 돌려준다"""
        pass

    @abstractmethod
    async def find_by_reserv_id(self, reserv_id : int) -> Reservation:
        """2) 예매 ID 찾기 없으면 None 반환()"""