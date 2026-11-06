"""
예매 가능여부 확인
약속만, 구현은 infrastructure
    1) 한 회원은 한 회차에 예매확정(CONFIRMED) 예매를 1건만 가질 수 있다
    2) 예매 취소하면 다시 예매할 수 있다
"""

from abc import ABC, abstractmethod

class ReservationChecker(ABC):
    @abstractmethod
    async def is_reserv_possible(
        self,
        ticketholder_id: int,
        perf_id: int
        ) -> bool:
        """이 회원이 이 회차에 예매할 수 있는지 확인 -> 확정된 예매가 없으면 가능"""
        pass
