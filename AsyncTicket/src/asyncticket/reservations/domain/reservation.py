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

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal # total_amount

from asyncticket.reservations.domain.enums import ReservationStatus # 요구사항 1번


@dataclass(kw_only=True) 
# dataclass 기능 : __init__을 자동으로 만들어
# kw_only=True : 키워드를 명시해 타입이 같은 값의 순서를 바꿔 넣는 실수를 방지

class Reservation:
    """예매 엔티티 (애그리거트 루트)"""

    # 값이 반드시 있어야 하는 필드
    user_id: int
    perf_id: int
    order_number: str
    total_amount: Decimal
    status: ReservationStatus

    # 기본값이 있는 필드
    quantity: int = 1 # 요구사항 3 : 1건 = 1좌석
    reserv_id: int | None = None # DB 저장 전에만 None 저장 후에는 항상 값이 있

    # 일시 
    created_at: datetime | None=None # DB에 저장되기 전에는 생성일이 없다
    confirmed_at: datetime | None=None
    canceled_at: datetime | None=None

