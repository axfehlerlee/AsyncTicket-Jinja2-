# <좌석 상태·등급 약속>
# - 상태 이름은 정의하되 선점·확정·해제의 전이 시점은 호출부와 맞춘다.

# seats/domain/enums.py
from enum import StrEnum

class SeatStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    OCCUPIED = "OCCUPIED"
    def is_reserved(self) -> bool:
        return self == SeatStatus.RESERVED

class SeatGrade(StrEnum):
    R = "R석"
    S = "S석"