"""수정 ERD의 seats_info를 표현하는 순수 파이썬 도메인.

FastAPI, SQLAlchemy와 DB 세션을 여기서 사용하지 않는다.
performance_seats의 생성 시점과 reserv_id의 NULL 정책은 별도 결정이다.
"""

from dataclasses import dataclass


def _require_integer(value: int, field_name: str, minimum: int) -> None:
    """bool과 문자열을 제외한 정수인지, 업무상 최솟값을 지키는지 검사한다."""
    if type(value) is not int or value < minimum:
        raise ValueError(f"{field_name}은(는) {minimum} 이상의 정수여야 한다.")


@dataclass(frozen=True, kw_only=True)
class SeatInfo:
    """한 회차의 좌석 등급 설정. ERD의 미입력(NULL) 상태도 표현한다.

    seat_id는 등급 설정의 번호다. 개별 판매 좌석의 perf_seat_id와 다르다.
    한 사람의 최대 예매 매수와 결제 여부는 이 클래스가 결정하지 않는다.
    """

    seat_id: int
    perf_id: int
    name: str | None = None
    total_seat: int | None = None
    price: int | None = None

    def __post_init__(self) -> None:
        """객체를 만들 때 잘못된 번호, 좌석 수, 가격을 차단한다."""
        _require_integer(self.seat_id, "좌석 등급 번호", 1)
        _require_integer(self.perf_id, "회차 번호", 1)
        if self.name is not None:
            if not isinstance(self.name, str) or len(self.name) > 255:
                raise ValueError("좌석 등급명은 255자 이하의 문자열이어야 한다.")
        if self.total_seat is not None:
            _require_integer(self.total_seat, "전체 좌석 수", 0)
        if self.price is not None:
            _require_integer(self.price, "가격", 0)

    def require_configured(self) -> None:
        """판매 규칙을 검사하기 전에 등급 설정이 갖춰졌는지 확인한다."""
        if self.name is None or not self.name.strip():
            raise ValueError("좌석 등급명을 먼저 설정해야 한다.")
        if self.total_seat is None:
            raise ValueError("전체 좌석 수를 먼저 설정해야 한다.")
        if self.price is None:
            raise ValueError("판매 가격을 먼저 설정해야 한다.")

    def remaining_seats(self, occupied_count: int) -> int:
        """호출자가 계산해 준 점유 수로 남은 좌석 수를 계산한다.

        무엇을 점유로 셀지는 외부 계약이다. 이 함수는 DB를 조회하거나
        좌석을 선점하지 않으며, 동시 예매를 막는 잠금도 수행하지 않는다.
        """
        _require_integer(occupied_count, "점유 좌석 수", 0)
        if self.total_seat is None:
            raise ValueError("전체 좌석 수를 먼저 설정해야 한다.")
        if occupied_count > self.total_seat:
            raise ValueError("점유 좌석 수가 전체 좌석 수보다 많다.")
        return self.total_seat - occupied_count

    def require_capacity(self, quantity: int, occupied_count: int) -> None:
        """요청한 매수를 수용할 수 있는지 검사한다. 실제 예매 처리는 아니다."""
        _require_integer(quantity, "요청 매수", 1)
        self.require_configured()
        if quantity > self.remaining_seats(occupied_count):
            raise ValueError("남은 좌석이 부족하다.")
