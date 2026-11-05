# 도메인: 회차별 좌석 등급의 정보와 수량·가격 규칙을 정의한다.
# 현재 값 속성은 기본 자료형으로 표현하며, 별도 VO 클래스는 없다.

from dataclasses import dataclass
from asyncticket.seats.domain.performanc_seat import PerformanceSeat


# 좌석 등급 엔티티. seat_id로 등급을 식별한다.
# dataclass의 기본 ==는 ID만이 아니라 모든 필드를 비교한다.
@dataclass(kw_only=True)
class SeatInfo:
    perf_id: int  # 소속 공연 회차 ID
    name: str  # 등급명: R석, S석 등
    total_seat: int  # 이 등급의 전체 좌석 수
    price: int  # 한 자리 가격
    seat_id: int | None = None  # 등급 ID. 신규 객체는 아직 ID가 없다.

    # 생성 직후 ID·등급명·수량·가격의 범위를 검사한다.
    def __post_init__(self) -> None:
        if self.perf_id <= 0:
            raise ValueError("회차 ID는 1 이상이어야 합니다.")

        if self.seat_id is not None and self.seat_id <= 0:
            raise ValueError("좌석 등급 ID는 1 이상이어야 합니다.")

        if not self.name.strip():
            raise ValueError("좌석 등급명은 비어 있을 수 없습니다.")

        if self.total_seat <= 0:
            raise ValueError("좌석 수는 1 이상이어야 합니다.")

        # 최소 50,000원은 현재 학습 기준이며, 팀 최종 정책은 미정이다.
        if self.price < 50000:
            raise ValueError("가격은 50000 이상이어야 합니다.")

    # 전체 좌석 수에서 호출자가 전달한 점유 수를 빼 잔여석을 구한다.
    def remaining_seats(self, occupied_count: int) -> int:
        if occupied_count < 0:
            raise ValueError("점유 좌석 수는 음수일 수 없습니다.")

        if occupied_count > self.total_seat:
            raise ValueError("점유 좌석 수가 전체 좌석 수보다 많습니다.")

        return self.total_seat - occupied_count

    # 요청 매수가 1 이상이고 잔여석 이내인지 검사한다.
    def require_capacity(self, quantity: int, occupied_count: int) -> None:
        if quantity <= 0:
            raise ValueError("요청 매수는 1 이상이어야 합니다.")

        if quantity > self.remaining_seats(occupied_count):
            raise ValueError("남은 좌석이 부족합니다.")

    # ID가 없는 신규 좌석 등급 객체를 만든다.
    @classmethod
    def create(
        cls,
        *,
        perf_id: int,
        name: str,
        total_seat: int,
        price: int,
    ) -> "SeatInfo":
        return cls(
            perf_id=perf_id,
            name=name,
            total_seat=total_seat,
            price=price,
        )

    # 등급 ID와 좌석명 목록으로 개별 좌석 객체를 만든다.
    def create_seats(self, seat_seqs: list[str]) -> list[PerformanceSeat]:
        if self.seat_id is None:
            raise ValueError("등급을 먼저 저장해야 합니다.")

        if len(seat_seqs) != self.total_seat:
            raise ValueError("좌석명 개수와 등급 좌석 수가 일치해야 합니다.")

        if len(set(seat_seqs)) != len(seat_seqs):
            raise ValueError("중복된 좌석명이 있습니다.")

        return [
            PerformanceSeat(
                seat_id=self.seat_id,
                seat_seq=seat_seq,
                # 초기 상태 AVAILABLE은 임시 기준이다.
                status="AVAILABLE",
            )
            for seat_seq in seat_seqs
        ]
