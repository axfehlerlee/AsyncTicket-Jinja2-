"""
요구사항 정의

1. 예매는 2가지 상태로 관리 
    - 예매확정(CONFIRMED), - 예매취소(CANCELED)
"""

from enum import StrEnum

# 비즈니스 요구사항 1 - 예매상태 관리
class ReservationStatus(StrEnum):
    CONFIRMED = "CONFIRMED" # 예매확정
    CANCELED = "CANCELED"   # 예매취소