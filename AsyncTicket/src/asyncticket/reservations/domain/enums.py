"""
요구사항 정의

1. 예매는 2가지 상태로 관리 
    - 예매확정(CONFIRMED), - 예매취소(CANCELED)
2. PENDING(결제 대기)과 EXPIRED(만료)를 추가로 관리할지 논의가 필요
"""

from enum import StrEnum

# 비즈니스 요구사항 1 - 예매상태 관리
class ReservationStatus(StrEnum):
    CONFIRMED = "CONFIRMED" # 예매확정
    CANCELED = "CANCELED"   # 예매취소