"""회차에 배정된 개별 판매 좌석의 순수 파이썬 도메인."""

from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class PerformanceSeat:
    """조회한 개별 판매 좌석. seat_id는 등급 ID, perf_seat_id는 좌석 PK다."""

    perf_seat_id: int
    seat_id: int
    perf_id: int
    grade: str | None
    seat_seq: str | None
    price: int | None
    status: str
