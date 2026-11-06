from dataclasses import dataclass
from asyncticket.seats.domain.enums import SeatGrade, SeatStatus
from asyncticket.seats.domain.performanc_seat import PerformanceSeat


@dataclass(frozen=True, kw_only=True)
class SeatInfo:
    """특정 공연 회차의 좌석 등급."""

    perf_id: int
    name: SeatGrade
    total_seat: int
    price: int
    seat_id: int | None = None

    def __post_init__(self) -> None:
        if type(self.perf_id) is not int or self.perf_id <= 0:
            raise ValueError("회차 ID는 1 이상이어야 합니다.")

        if self.seat_id is not None and (
            type(self.seat_id) is not int or self.seat_id <= 0
        ):
            raise ValueError("좌석 등급 ID는 1 이상이어야 합니다.")

        if not isinstance(self.name, SeatGrade):
            raise ValueError("좌석 등급은 SeatGrade 타입이어야 합니다.")

        if type(self.total_seat) is not int or self.total_seat <= 0:
            raise ValueError("좌석 수는 1 이상이어야 합니다.")

        if type(self.price) is not int or self.price < 0:
            raise ValueError("가격은 0 이상이어야 합니다.")

    def remaining_seats(self, occupied_count: int) -> int:
        if type(occupied_count) is not int or occupied_count < 0:
            raise ValueError("점유 좌석 수는 음수일 수 없습니다.")

        if occupied_count > self.total_seat:
            raise ValueError("점유 좌석 수가 전체 좌석 수보다 많습니다.")

        return self.total_seat - occupied_count

    def require_capacity(self, quantity: int, occupied_count: int) -> None:
        if type(quantity) is not int or quantity <= 0:
            raise ValueError("요청 매수는 1 이상이어야 합니다.")

        if quantity > self.remaining_seats(occupied_count):
            raise ValueError("남은 좌석이 부족합니다.")

    @classmethod
    def create(
        cls,
        *,
        perf_id: int,
        name: SeatGrade,
        total_seat: int,
        price: int,
    ) -> "SeatInfo":
        return cls(
            perf_id=perf_id,
            name=name,
            total_seat=total_seat,
            price=price,
        )

    def validate_seat_names(self, seat_seqs: list[str]) -> None:
        if len(seat_seqs) != self.total_seat:
            raise ValueError("좌석명 개수와 등급 좌석 수가 일치해야 합니다.")

        for seat_seq in seat_seqs:
            PerformanceSeat.validate_seat_seq(seat_seq)

        if len(set(seat_seqs)) != len(seat_seqs):
            raise ValueError("중복된 좌석명이 있습니다.")

    def create_seats(self, seat_seqs: list[str]) -> list[PerformanceSeat]:
        if self.seat_id is None:
            raise ValueError("등급을 먼저 저장해야 합니다.")
        self.validate_seat_names(seat_seqs)

        return [
            PerformanceSeat(
                seat_id=self.seat_id,
                seat_seq=seat_seq,
                # 초기 상태 AVAILABLE은 임시 기준이다.
                status=SeatStatus.AVAILABLE,
            )
            for seat_seq in seat_seqs
        ]
