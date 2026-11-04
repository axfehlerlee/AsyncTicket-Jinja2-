# 도메인 비즈니스 요구사항 정의하기
"""
요구사항 정의

1. 예매는 2가지 상태로 관리 
    - 예매확정(CONFIRMED), 예매취소(CANCELED)
2. 예매는 결제가 성공했을 때만 생성되며, 생성되면 바로 예매확정(CONFIRMED)
3. 예매 1건에는 좌석 1개만 예매할 수 있다 (quantity = 1)
4. 예매 금액은 좌석 등급의 가격으로 정하고, 0원보다 커야한다 -> 좌석에서 정하는것?
5. 한 회원은 한 회차에 예매확정(CONFIRMED) 예매를 1건만 가질 수 있다
    - 예매를 취소하면 다시 예매할 수 있다
6. 예매 취소
    - 예매확정(CONFIRMED) 상태에서만 가능
    - 공연 시작 전까지만 취소할 수 있다
    - 취소하면 예매 상태는 예매취소(CANCELED)가 되고 취소 일 기록(null -> date생성)
7. 예매ID, 회원ID, 회차ID, 매수, 금액, 상태, 예매·확정·취소 일시를 확인할 수 있다

"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal # total_amount

from asyncticket.reservations.domain.enums import ReservationStatus # 요구사항 1번


# 0. 예매 예외
class ReservationError(Exception) :
    """예매 도메인 예외의 공통 부모"""
    def __init__(self, message:str, error_code:str):
        self.message = message  
        self.error_code = error_code
        super().__init__(message)

class ReservationValidationError(ReservationError):
    """값이 예매 규칙에 맞지 않음(요구사항 3,4)"""

# 1. VO (Value Object)
@dataclass(frozen=True, kw_only=True)
class ReservationPerson:      
    """예매자 (reservations.user_id)"""
    reservation_person_id: int
    reservation_person_name: str

@dataclass(frozen=True, kw_only=True)
class ReservationPerformanceInfo:
    """예매한 회차 정보(performances, shows)"""
    show_title: str
    perf_id: int
    round_number: int
    starts_at: datetime

@dataclass(frozen=True, kw_only=True)
class ReservationSeat:
    """예매한 좌석 정보 (performance_seats, seats_info)"""
    perf_seat_id: int
    seat_number: str | None
    seat_grade: str
    seat_price: int

@dataclass(frozen=True, kw_only=True)
class ReservationPaymentInfo: 
    """예약 결제정보 (payments)"""
    pay_id: int | None = None
    payment_status: str
    paid_at: datetime | None = None 


# 2. 엔티티
@dataclass(kw_only=True)
class Reservation:
    """예매 엔티티 (애그리거트 루트)"""

    # 1) VO 정보들
    person:ReservationPerson 
    performance:ReservationPerformanceInfo
    seat:ReservationSeat
    payment:ReservationPaymentInfo

    # 2) 예매 자신의 정보
    order_number: str
    total_amount: Decimal
    status: ReservationStatus
    quantity: int = 1               # 요구사항 3 : 1건 = 1좌석
    reserv_id: int | None = None    # DB 저장 전에만 None 저장 후에는 항상 값이 있음
    created_at: datetime | None=None # DB에 저장되기 전에는 생성일이 없다
    confirmed_at: datetime | None=None
    canceled_at: datetime | None=None

    # 3) 예매가 생성될 때마다 항상 검사하는 규칙 
    def __post_init__(self):

        # 요구사항 3 : 예매 1건 = 좌석 1개
        if self.quantity != 1 :
            raise ReservationValidationError(
                message="예매 1건에는 좌석 1개만 예매할 수 있습니다",
                error_code="INVALID_QUANTITY"
            )

        # 요구사항 4 : 금액은 0원보다 커야한다
        if self.total_amount <= 0 :
            raise ReservationValidationError(
                message="예매 금액은 0원보다 커야합니다",
                error_code="INVALID_TOTAL_AMOUNT"
            )

    # 4) 새 예매를 만드는 방법 (요구사항 2 : 생성되면 바로 CONFIRMED)
    @classmethod
    def confirm_new(
        cls,
        *, 
        person: ReservationPerson, 
        performance: ReservationPerformanceInfo, 
        seat: ReservationSeat, 
        payment: ReservationPaymentInfo,
        order_number: str,
        now: datetime, ) -> "Reservation" : 
        
        return cls(
            person=person,
            performance=performance,
            seat=seat,
            payment=payment,
            order_number=order_number,
            total_amount=Decimal(seat.seat_price),  # 요구사항 4 : 예매금액 = 좌석 가격
            status=ReservationStatus.CONFIRMED,
            confirmed_at=now
        )