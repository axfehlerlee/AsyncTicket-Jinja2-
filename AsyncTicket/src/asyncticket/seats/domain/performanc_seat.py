# 도메인: 등급에 속한 개별 좌석의 정보와 기본 값 검사를 정의한다.
# 업무 흐름: 등급·가격·수량 등록 → 잔여석·배치 확인 → 좌석 선택 → 결제 → 성공 후 예매 확정.
# 현재 이 객체에는 상태 변경과 예매 연결·해제 기능이 없다.
# 미정: 결제 중 점유, 취소 시 해제 조건, 좌석 배치 저장 방식.
# 공연 시작·종료 시 초기화와 알림은 현재 요구사항에 포함되지 않는다.

from dataclasses import dataclass


# 개별 좌석 엔티티. perf_seat_id로 자리를 식별한다.
# frozen=True는 필드 재할당을 막는 설정이며, VO를 뜻하지 않는다.
# dataclass의 기본 ==는 ID만이 아니라 모든 필드를 비교한다.
@dataclass(frozen=True, kw_only=True)
class PerformanceSeat:
    seat_id: int  # 소속 좌석 등급 ID
    seat_seq: str  # 좌석명: A01, A02 등
    status: str  # 현재 좌석 상태
    perf_seat_id: int | None = None  # 개별 좌석 ID. 신규 객체는 아직 ID가 없다.
    reserv_id: int | None = None  # 연결된 예매 ID. 연결 전에는 None이다.

    # 생성 직후 ID 범위와 좌석명·상태의 빈 문자열 여부를 검사한다.
    def __post_init__(self) -> None:
        if self.perf_seat_id is not None and self.perf_seat_id <= 0:
            raise ValueError("개별 좌석 ID는 1 이상이어야 합니다.")

        if self.seat_id <= 0:
            raise ValueError("좌석 등급 ID는 1 이상이어야 합니다.")

        if not self.seat_seq.strip():
            raise ValueError("좌석명은 비어 있을 수 없습니다.")

        if not self.status.strip():
            raise ValueError("좌석 상태는 비어 있을 수 없습니다.")

        if self.reserv_id is not None and self.reserv_id <= 0:
            raise ValueError("예매 ID는 1 이상이어야 합니다.")
