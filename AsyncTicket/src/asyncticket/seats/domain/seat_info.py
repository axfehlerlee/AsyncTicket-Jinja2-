# 도메인이 업무 규칙을 책임지기 때문에 검증
# 좌석 등급 정보 (SeatInfo)
# - 특정 회차의 등급명, 한 자리 가격, 전체 좌석 수를 가진다.
# - 가격과 좌석 수가 올바른지 검사한다.
# - 전달받은 점유 좌석 수로 해당 등급의 잔여 좌석 수를 계산한다.
# - 점유 좌석 수를 얻는 DB 조회는 저장소가 맡는다.

from dataclasses import dataclass
from asyncticket.seats.domain.performanc_seat import PerformanceSeat

# 좌석 등급 도메인: 한 회차의 R석 같은 등급명·가격·전체 좌석 수를 표현한다.
# 생성 값과 요청 매수를 검사하고, 전달받은 점유 수로 잔여석을 계산한다. DB 조회는 하지 않는다.
# [엔티티] seat_id로 구별하는 좌석 등급이다. 가격이 바뀌어도 같은 등급일 수 있다.
# 주의: 현재 dataclass의 기본 ==는 모든 필드를 비교한다. ID 기준 비교는 별도 구현하지 않았다.
@dataclass(kw_only=True)
class SeatInfo:
    # [다른 엔티티 참조] 이 등급이 속한 공연 회차의 ID다.
    perf_id: int

    # [값 속성] 등급의 이름과 수량이다. 현재는 str·int로 표현하며 별도 VO는 없다.
    name: str
    total_seat: int

    # [VO 분리 후보] 가격은 현재 int다. 금액과 가격 검증을 묶는 Price VO로 분리할 수 있다.
    # 지금 코드에는 Price 클래스가 없으며, 가격 검증은 아래 __post_init__에서 수행한다.
    price: int

    # [엔티티 자신의 ID] 새 등급은 None이고, 저장소의 flush 후 DB가 발급한 값을 받는다.
    seat_id: int | None = None

    def __post_init__(self) -> None:
        if self.perf_id <= 0:
            raise ValueError("회차 ID는 1 이상이어야 합니다.")

        if self.seat_id is not None and self.seat_id <= 0:
            raise ValueError("좌석 등급 ID는 1 이상이어야 합니다.")

        if not self.name.strip():
            raise ValueError("좌석 등급명은 비어 있을 수 없습니다.")

        if self.total_seat <= 0:
            raise ValueError("좌석 수는 1 이상이어야 합니다.")

        if self.price < 50000:
            raise ValueError("가격은 50000 이상이어야 합니다.")

    def remaining_seats(self, occupied_count: int) -> int:
        if occupied_count < 0:
            raise ValueError("점유 좌석 수는 음수일 수 없습니다.")

        if occupied_count > self.total_seat:
            raise ValueError("점유 좌석 수가 전체 좌석 수보다 많습니다.")

        return self.total_seat - occupied_count

    def require_capacity(self, quantity: int, occupied_count: int) -> None:
        if quantity <= 0:
            raise ValueError("요청 매수는 1 이상이어야 합니다.")

        if quantity > self.remaining_seats(occupied_count):
            raise ValueError("남은 좌석이 부족합니다.")

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
                status="AVAILABLE",
            )
            for seat_seq in seat_seqs
        ]
