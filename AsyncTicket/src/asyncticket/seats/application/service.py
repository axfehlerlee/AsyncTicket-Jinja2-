# 응용 계층: 저장소 계약을 통해 조회·도메인 검사·저장의 순서를 조율한다.
# 좌석의 DB 구현·API·wiring·트랜잭션 연결은 아직 작성 전이다.

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


# 좌석 등급 작업과 등급별 개별 좌석 생성을 조율한다.
class SeatInfoService:
    # 등급 저장소와 개별 좌석 저장소의 구현을 외부에서 전달받는다.
    def __init__(
        self,
        repository: SeatInfoRepository,
        performance_seat_repository: PerformanceSeatRepository,
    ):
        self.repository = repository
        self.performance_seat_repository = performance_seat_repository

    # 저장소에 좌석 등급 조회를 요청한다.
    async def get_seat_info(self, seat_id: int) -> SeatInfo:
        return await self.repository.get_seat_info(seat_id)

    # 저장소에 좌석 등급 저장을 요청한다.
    async def save_seat_info(self, seat_info: SeatInfo) -> SeatInfo:
        return await self.repository.save_seat_info(seat_info)

    # 등급을 조회하고, 전달받은 점유 수로 요청 매수를 검사한다.
    async def check_seat_availability(
        self, seat_id: int, quantity: int, occupied_count: int
    ) -> None:
        seat_info = await self.get_seat_info(seat_id)
        seat_info.require_capacity(quantity, occupied_count)

    # check_seat_availability와 같은 검사이며, 현재 두 메서드가 중복된다.
    async def check_capacity(
        self, seat_id: int, quantity: int, occupied_count: int
    ) -> None:
        seat_info = await self.get_seat_info(seat_id)
        seat_info.require_capacity(quantity, occupied_count)

    # 회차 확인·잠금 → 중복 검사 → 등급 저장 → 좌석 생성·저장 순서로 진행한다.
    async def create_seat_configuration(
        self,
        seat_info: SeatInfo,
        seat_seqs: list[str],
    ) -> SeatInfo:
        # 회차가 없으면 저장 작업을 중단한다.
        if not await self.repository.lock_performance(seat_info.perf_id):
            raise NotFoundException(
                "회차를 찾을 수 없습니다.",
                error_code="PERFORMANCE_NOT_FOUND",
            )

        # 같은 회차의 등급명 중복을 거절한다.
        if await self.repository.grade_exists(seat_info.perf_id, seat_info.name):
            raise ConflictException("같은 회차에 이미 등록된 좌석 등급입니다.")

        # 같은 회차의 좌석명 중복을 거절한다.
        if await self.performance_seat_repository.names_exist(
            seat_info.perf_id, seat_seqs
        ):
            raise ConflictException("같은 회차에 이미 등록된 좌석명입니다.")

        # 저장소에서 ID를 받은 뒤, 그 ID에 속한 개별 좌석을 만든다.
        saved_grade = await self.repository.save_seat_info(seat_info)

        seats = saved_grade.create_seats(seat_seqs)

        # 생성한 좌석 목록을 저장소에 전달한다.
        await self.performance_seat_repository.save_many(seats)

        return saved_grade


# 개별 좌석 목록 저장을 저장소에 요청한다.
class PerformanceSeatService:
    def __init__(self, repository: PerformanceSeatRepository):
        self.repository = repository

    async def save_many(self, seats: list[PerformanceSeat]) -> None:
        await self.repository.save_many(seats)
