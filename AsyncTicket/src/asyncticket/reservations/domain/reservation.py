# 도메인 비즈니스 요구사항 정의하기
"""
요구사항 정의

1. 예매는 2가지 상태로 관리 
    - 예매확정(CONFIRMED), 예매취소(CANCELED)
2. 예매는 결제가 성공했을 때만 생성되며, 생성되면 바로 예매확정(CONFIRMED)
3. 예매 1건에는 좌석 1개만 예매할 수 있다 (quantity = 1)
4. 예매 금액은 좌석 등급의 가격으로 정하고, 0원보다 커야한다
5. 한 회원은 한 회차에 예매확정(CONFIRMED) 예매를 1건만 가질 수 있다
    - 예매를 취소하면 다시 예매할 수 있다
6. 예매 취소
    - 예매확정(CONFIRMED) 상태에서만 가능
    - 공연 시작 전까지만 취소할 수 있다
    - 취소하면 예매 상태는 예매취소(CANCELED)가 되고 취소 일가 기록(null -> date생성)
7. 예매ID, 회원ID, 회차ID, 매수, 금액, 상태, 예매·확정·취소 일시를 확인할 수 있다

"""

from datetime import datetime
from domain.enums import ReservationStatus


# 

# # 예매가 가진값들
# class Reservation:
#     def __init__(self, 
#                 reserv_id: int, 
#                 user_id: int, 
#                 perf_id: int, 
#                 total_amount: int, 
#                 status: str):
        
#         self.id = reserv_id
#         self.user_id = user_id
#         self.perf_id = perf_id
#         self.quantity = 1 # 1인 예매 1좌석 한정
#         self.total_amount = total_amount
#         self.status = status
#         self.created_at = None #datetime.now()
#         self.confirmed_at = None
#         self.canceled_at = None


    # @classmethod
    # # 예매 생성 규칙
    # def create(self, reserv_id: int, user_id: int, perf_id: int, ):
    #     NotImplementedError

    # # 예매 취소 규칙
    