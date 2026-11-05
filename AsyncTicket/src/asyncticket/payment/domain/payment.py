from enum import Enum
from decimal import Decimal
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timezone

class PaymentStatus(str, Enum):
    FAILED = "FAIL"
    PAID = "SUCCESS"
    REFUNDED = "REFUND"

@dataclass
class Payment:
    """
    결제 엔티티.
    - 실패: 예매와 연결되면 안 됨
    - 성공/환불: 예매와 연결되어 있어야 함
    - 환불은 성공 이후에만 가능
    - 예매 생성·좌석 처리·DB 저장은 하지 않음
    """
    pay_id: Optional[int]
    method: str 
    amount: Decimal 
    status: PaymentStatus 
    reserv_id: Optional[int] = None 
    created_at: Optional[datetime] = None 
    paid_at: Optional[datetime] = None 
    refunded_at: Optional[datetime] = None 

    # 객체를 만들자마자 규칙을 검사
    def __post_init__(self) -> None:
        self._validate_invariant()


    def _validate_invariant(self) -> None:
        # 결제가 성공해야 예매가 확정된다
        if self.status == PaymentStatus.FAILED and self.reserv_id is not None:
            raise ValueError("결제를 실패했으면 예매와 연결될 수 없습니다.")
        # 성공하거나 환불된 결제는 반드시 예매와 연결되어 있어야 한다
        if self.status in (PaymentStatus.PAID,PaymentStatus.REFUNDED) and self.reserv_id is None:
            raise ValueError("성공/환불 상태의 결제는 예매와 연결되어 있어야 합니다.")

    def mark_as_failed(self) -> None:
        """결제 시도 실패. 예매가 없어야 함."""
        # 성공/환불된 결제를 실패로 덮어씌우는 것을 방지
        if self.status != PaymentStatus.FAILED and self.reserv_id is not None:
            raise ValueError("이미 예매와 연결된 결제는 실패로 바꿀 수 없습니다.")
        self.status = PaymentStatus.FAILED
        self.reserv_id = None
        self._validate_invariant()

    def mark_as_paid(self, reserv_id: int, paid_at: Optional[datetime] = None) -> None:
        """
        성공 처리.
        예매 ID는 바깥(애플리케이션/포트)에서 생성·확정 후 전달받는다.
        """
        if self.status == PaymentStatus.REFUNDED:
            raise ValueError("환불된 결제는 다시 성공으로 바꿀 수 없습니다.")
        if reserv_id is None:
            raise ValueError("성공 상태에는 예매 ID가 필요합니다.")
        self.status = PaymentStatus.PAID
        self.reserv_id = reserv_id
        self.paid_at = paid_at or datetime.now(timezone.utc)
        self._validate_invariant()


    def mark_as_refunded(self, refunded_at: Optional[datetime] = None) -> None:
        """
        환불 처리.
        예매 도메인에서 취소가 시작된 뒤에만 호출되어야 한다.
        """
        if self.status != PaymentStatus.PAID:
            raise ValueError("성공 상태인 결제만 환불할 수 있습니다.")
        if self.reserv_id is None:
            raise ValueError("예매와 연결되지 않은 결제는 환불할 수 없습니다.")
        self.status = PaymentStatus.REFUNDED
        self.refunded_at = refunded_at or datetime.now(timezone.utc)
        self._validate_invariant()

    @property
    def is_linked_to_reservation(self) -> bool:
        return self.reserv_id is not None