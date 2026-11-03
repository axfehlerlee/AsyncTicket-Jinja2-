from enum import StrEnum

# 비즈니스 요구사항 1 - 예매상태 관리
class ReservationStatus(StrEnum):
    CONFIRMED = "CONFIRMED" # 예매확정
    CANCELED = "CANCELED"   # 예매취소