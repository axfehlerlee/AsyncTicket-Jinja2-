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