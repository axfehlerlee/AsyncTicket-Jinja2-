# [응용 계층: 좌석 등급 서비스]
# 사용자의 작업을 처리하기 위해 조회 → 도메인 검사 → 저장 같은 순서를 조율한다.
# SQL을 직접 실행하거나 좌석 수용량 규칙을 여기서 다시 작성하지 않는다.
#
# [저장소를 생성자에서 받는 이유]
# SeatInfoRepository는 도메인에 있는 계약(필요한 조회·저장 기능)이다.
# wiring이 실제 SqlAlchemySeatInfoRepository를 만들어 서비스에 넣어준다.
# 서비스는 실제 DB 구현을 몰라도 되고, 테스트에서는 계약에 맞는 대역 저장소를 받을 수 있다.
#
# [조회: get_seat_info]
# 서비스.get_seat_info(등급 ID) → 저장소.get_seat_info(등급 ID)
# → 인프라에서 SQLAlchemy로 조회 → ORM 모델을 SeatInfo로 변환 → 서비스가 반환.
# ORM은 Object-Relational Mapping(객체-관계 매핑)이며, 모델은 DB 테이블에 대응하는 객체다.
# 도메인 객체를 만드는 순간 __post_init__의 검증도 실행된다.
#
# [저장: save_seat_info]
# 서비스가 SeatInfo를 저장소에 전달 → 인프라에서 ORM 모델 생성 → add → flush
# → DB가 발급한 ID를 담은 SeatInfo를 저장소가 반환 → 서비스가 호출자에 반환.
# 현재 저장소 구현은 새 행 추가용이며, 기존 행 수정 기능까지 구현된 것은 아니다.
# flush는 SQL을 DB로 보내는 단계이고, commit(최종 확정)과 다르다.
# 현재 이 서비스에는 commit·rollback 연결이 없다. ID를 받았다고 최종 저장 완료는 아니다.
# 다음 작업: 작업 전체가 성공하면 commit, 실패하면 rollback하도록 기존 팀 방식에 맞춰 연결.
#
# [수용량 검사: check_seat_availability / check_capacity]
# 저장소에서 SeatInfo 조회 → 도메인의 require_capacity(요청 매수, 점유 수)를 호출한다.
# 도메인이 잔여석을 계산하고 부족하면 ValueError를 발생시킨다. 서비스는 검사 순서를 조율한다.
# 점유 수는 현재 호출자가 전달한다. 실제 DB 점유 수 조회·동시 요청 방어는 아직 연결하지 않았다.
# 두 메서드는 현재 같은 기능으로 중복되어 있으므로, 함께 사용할 이름을 정해 추후 정리한다.
# 이 검사는 등급의 수량 검사이며, 특정 A01 좌석의 예매 가능 상태를 확인하는 검사는 아니다.
#
# [표현 계층과의 경계]
# HTTP 입력 검증·응답 스키마·오류 응답 변환은 라우터/Pydantic/예외 처리기의 역할이다.
# 이 서비스는 요청·응답 객체 대신 등급 ID, SeatInfo 같은 값과 객체를 주고받는다.

from asyncticket.seats.domain.repository import (
    SeatInfoRepository,
    PerformanceSeatRepository,
)
from asyncticket.seats.domain.performanc_seat import PerformanceSeat
from asyncticket.seats.domain.seat_info import SeatInfo
from asyncticket.shared.core.exceptions import (
    ConflictException,
    NotFoundException,
)


class SeatInfoService:
    def __init__(
        self,
        repository: SeatInfoRepository,
        performance_seat_repository: PerformanceSeatRepository,
    ):
        self.repository = repository
        self.performance_seat_repository = performance_seat_repository

    async def get_seat_info(self, seat_id: int) -> SeatInfo:
        return await self.repository.get_seat_info(seat_id)

    async def save_seat_info(self, seat_info: SeatInfo) -> SeatInfo:
        return await self.repository.save_seat_info(seat_info)

    async def check_seat_availability(
        self, seat_id: int, quantity: int, occupied_count: int
    ) -> None:
        seat_info = await self.get_seat_info(seat_id)
        seat_info.require_capacity(quantity, occupied_count)

    async def check_capacity(
        self, seat_id: int, quantity: int, occupied_count: int
    ) -> None:
        seat_info = await self.get_seat_info(seat_id)
        seat_info.require_capacity(quantity, occupied_count)

    async def create_seat_configuration(
        self,
        seat_info: SeatInfo,
        seat_seqs: list[str],
    ) -> SeatInfo:
        # 회차가 존재하는지 확인하고, 변경 작업을 위한 잠금을 잡는다.
        if not await self.repository.lock_performance(seat_info.perf_id):
            raise NotFoundException(
                "회차를 찾을 수 없습니다.",
                error_code="PERFORMANCE_NOT_FOUND",
            )

        # 같은 회차의 등급명 중복 검사
        if await self.repository.grade_exists(seat_info.perf_id, seat_info.name):
            raise ConflictException("같은 회차에 이미 등록된 좌석 등급입니다.")

        # 다른 등급을 포함한 회차 내 좌석명 중복 검사
        if await self.performance_seat_repository.names_exist(
            seat_info.perf_id, seat_seqs
        ):
            raise ConflictException("같은 회차에 이미 등록된 좌석명입니다.")
        # 1. 등급을 저장하고, DB가 발급한 ID가 있는 등급 객체를 받는다.
        saved_grade = await self.repository.save_seat_info(seat_info)

        # 2. 도메인에 좌석 생성을 맡긴다.
        # 수량·중복을 검사하고, 같은 등급 ID를 가진 좌석 객체들을 만든다.
        seats = saved_grade.create_seats(seat_seqs)

        # 3. 만들어진 좌석들을 저장 대상으로 등록한다.
        await self.performance_seat_repository.save_many(seats)

        # 4. 발급된 등급 ID를 포함한 결과를 호출자에게 돌려준다.
        return saved_grade


class PerformanceSeatService:
    def __init__(self, repository: PerformanceSeatRepository):
        self.repository = repository

    async def save_many(self, seats: list[PerformanceSeat]) -> None:
        await self.repository.save_many(seats)
