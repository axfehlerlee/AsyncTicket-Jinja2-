# 도메인이 업무 규칙을 책임지기 때문에 검증하
#  회차별 개별 좌석 (PerformanceSeat)
# - A01 같은 좌석명, 소속 등급 ID, 좌석 상태, 예매 연결 정보를 가진다.
# - 현재 상태에 따라 해당 좌석을 예매할 수 있는지 검사한다.
# - 확정된 규칙에 따라 예매 연결과 해제 시 상태 변경을 담당한다.
# - 등급명, 가격, 전체 좌석 수는 좌석 등급 정보(SeatInfo)의 책임이다.
#
# 함께 정리한 사용자 흐름
# 1. 판매자가 회차별 좌석 등급, 한 자리 가격, 좌석 수를 등록한다.
# 2. 관객이 등급별 잔여 좌석 수, 가격과 좌석 배치를 확인한다.
# 3. 관객이 원하는 개별 좌석을 선택한다.
# 4. 관객이 결제를 진행한다.
# 5. 결제 성공 후 예매를 생성·확정하고 해당 좌석 상태에 반영한다.
# 이 전체 흐름은 응용 서비스와 결제·예매 도메인이 협력하며, 이 객체 혼자 처리하지 않는다.
#
# 미정: 선택·결제 중 좌석 점유, 취소 시 해제 조건, 배치 정보 저장 방식.
# 공연 시작·종료 시 좌석 초기화와 알림 처리는 확정 요구사항에 포함하지 않는다.
from dataclasses import dataclass


# 개별 좌석 도메인: 등급에 속한 A01 같은 자리와 상태·예매 연결 정보를 표현한다.
# 현재는 ID·좌석명·상태의 기본 입력 검사까지 구현돼 있다. 예매 연결·해제 행위는 아직 없다.
# [엔티티] perf_seat_id로 구별하는 개별 좌석이다. 상태가 달라져도 같은 좌석일 수 있다.
# [불변 설정] frozen=True는 생성 후 필드 재할당을 막는다. 이것만으로 VO가 되는 것은 아니다.
# 주의: 현재 dataclass의 기본 ==는 모든 필드를 비교한다. ID 기준 비교는 별도 구현하지 않았다.
@dataclass(frozen=True, kw_only=True)
class PerformanceSeat:
    # [다른 엔티티 참조] 이 좌석이 속한 좌석 등급의 ID다.
    seat_id: int

    # [VO 분리 후보] A01 같은 좌석명은 현재 str다. 이름과 형식 검증을 묶는 VO로 분리할 수 있다.
    seat_seq: str

    # [값 속성] 현재 좌석 상태다. str이며 별도 VO나 상태 전이 규칙은 아직 없다.
    status: str

    # [엔티티 자신의 ID] 새 좌석은 None이고, DB 저장 과정에서 ID를 발급받는다.
    perf_seat_id: int | None = None

    # [다른 엔티티 참조] 연결된 예매의 ID다. 예매가 연결되지 않았으면 None이다.
    reserv_id: int | None = None

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
