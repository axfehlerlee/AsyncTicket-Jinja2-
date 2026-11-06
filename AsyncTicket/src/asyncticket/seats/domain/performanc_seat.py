# 1 예매 전용 좌석 도메인 (PerformanceSeat)

from dataclasses import dataclass

@dataclass(frozen=True, kw_only=True)
class PerformanceSeat:
    """좌석 등급에 속한 개별 좌석. 예매 연결 전 reserv_id는 None이다."""

    seat_id: int
    seat_seq: str
    status: str
    perf_seat_id: int | None = None
    reserv_id: int | None = None

    def __post_init__(self) -> None:
        if self.perf_seat_id is not None and (
            type(self.perf_seat_id) is not int or self.perf_seat_id <= 0
        ):
            raise ValueError("개별 좌석 ID는 1 이상이어야 합니다.")

        if type(self.seat_id) is not int or self.seat_id <= 0:
            raise ValueError("좌석 등급 ID는 1 이상이어야 합니다.")

        self.validate_seat_seq(self.seat_seq)

        if not isinstance(self.status, str) or not self.status.strip() or len(self.status) > 30:
            raise ValueError("좌석 상태는 공백이 아닌 1~30자여야 합니다.")

        if self.reserv_id is not None and (
            type(self.reserv_id) is not int or self.reserv_id <= 0
        ):
            raise ValueError("예매 ID는 1 이상이어야 합니다.")

    @staticmethod
    def validate_seat_seq(seat_seq: str) -> None:
        if not isinstance(seat_seq, str) or not seat_seq.strip() or len(seat_seq) > 255:
            raise ValueError("좌석명은 공백이 아닌 1~255자여야 합니다.")
