from dataclasses import replace
from datetime import datetime, timezone

from asyncticket.seats.domain.repository import (
    PerformanceSeatRepository,
    SeatInfoRepository,
    SeatLookupConflictError,
)
from asyncticket.seats.domain.seat_info import SeatInfo
from asyncticket.shared.core.exceptions import (
    ConflictException,
    NotFoundException,
    SharedException,
)
from asyncticket.shared.domain.catalog import CatalogActor, CatalogPolicy


class SeatInfoService:
    def __init__(
        self,
        repository: SeatInfoRepository,
        performance_seat_repository: PerformanceSeatRepository,
        policy: CatalogPolicy,
    ) -> None:
        self.repository = repository
        self.performance_seat_repository = performance_seat_repository
        self.policy = policy

    async def get_seat_info(self, seat_id: int) -> SeatInfo:
        seat_info = await self.repository.get_seat_info(seat_id)
        if seat_info is None:
            raise NotFoundException(
                "좌석 등급을 찾을 수 없습니다.", error_code="SEAT_INFO_NOT_FOUND"
            )
        return seat_info

    async def save_seat_info(self, seat_info: SeatInfo) -> SeatInfo:
        try:
            if seat_info.seat_id is None:
                raise ValueError(
                    "신규 등급은 좌석명과 함께 create_seat_configuration으로 생성해야 합니다."
                )
            current = await self.get_seat_info(seat_info.seat_id)
            if not await self.repository.lock_performance(current.perf_id):
                raise NotFoundException(
                    "회차를 찾을 수 없습니다.", error_code="PERFORMANCE_NOT_FOUND"
                )
            current = await self.get_seat_info(seat_info.seat_id)
            if (seat_info.perf_id, seat_info.name, seat_info.total_seat) != (
                current.perf_id,
                current.name,
                current.total_seat,
            ):
                raise ValueError(
                    "기존 등급은 가격만 변경할 수 있습니다. 좌석 구성 변경은 아직 지원하지 않습니다."
                )
            saved_grade = await self.repository.save_seat_info(seat_info)
            await self.repository.commit()
            return saved_grade
        except BaseException:
            await self.repository.rollback()
            raise

    async def check_seat_availability(
        self,
        seat_id: int,
        quantity: int,
        occupied_count: int,
    ) -> None:
        seat_info = await self.get_seat_info(seat_id)
        seat_info.require_capacity(quantity, occupied_count)

    async def check_capacity(
        self,
        seat_id: int,
        quantity: int,
        occupied_count: int,
    ) -> None:
        await self.check_seat_availability(seat_id, quantity, occupied_count)

    async def create_seat_configuration(
        self,
        seat_info: SeatInfo,
        seat_seqs: list[str],
    ) -> SeatInfo:
        try:
            if seat_info.seat_id is not None:
                raise ValueError("새 좌석 구성에는 등급 ID를 지정할 수 없습니다.")
            seat_info.validate_seat_names(seat_seqs)

            # 같은 회차의 좌석 구성 생성을 직렬화한 뒤 중복을 검사한다.
            if not await self.repository.lock_performance(seat_info.perf_id):
                raise NotFoundException(
                    "회차를 찾을 수 없습니다.", error_code="PERFORMANCE_NOT_FOUND"
                )
            if await self.repository.grade_exists(seat_info.perf_id, seat_info.name):
                raise ConflictException("같은 회차에 이미 등록된 좌석 등급입니다.")
            if await self.performance_seat_repository.names_exist(
                seat_info.perf_id, seat_seqs
            ):
                raise ConflictException("같은 회차에 이미 등록된 좌석명입니다.")

            saved_grade = await self.repository.save_seat_info(seat_info)
            await self.performance_seat_repository.save_many(
                saved_grade.create_seats(seat_seqs)
            )
            await self.repository.commit()
            return saved_grade
        except BaseException:
            await self.repository.rollback()
            raise

    async def _authorize(self, perf_id: int, actor: CatalogActor) -> None:
        self.policy.authorize(actor)
        if not await self.repository.lock_performance(perf_id):
            raise NotFoundException(
                "공연 회차를 찾을 수 없습니다.", error_code="PERFORMANCE_NOT_FOUND"
            )
        context = await self.repository.get_management_context(perf_id)
        if context is None:
            raise NotFoundException(
                "공연 회차를 찾을 수 없습니다.", error_code="PERFORMANCE_NOT_FOUND"
            )
        owner_id = context["owner_id"]
        if type(owner_id) is not int or owner_id <= 0:
            raise SharedException(
                "공연 소유자 설정을 확인해야 합니다.",
                status_code=503,
                error_code="INVALID_SHOW_OWNER",
            )
        self.policy.authorize(actor, owner_id)
        booking_opens_at = context["booking_opens_at"]
        if not isinstance(booking_opens_at, datetime) or booking_opens_at.utcoffset() is None:
            raise SharedException(
                "회차 판매 시각 설정을 확인해야 합니다.",
                status_code=503,
                error_code="INVALID_BOOKING_TIME",
            )
        # 판매 시작 후 구성·가격 변경은 이 API에서 지원하지 않는다.
        if datetime.now(timezone.utc) >= booking_opens_at:
            raise ConflictException(
                "판매 시작 후 좌석 구성을 변경할 수 없습니다.",
                error_code="SEAT_SALE_STARTED",
            )

    async def create(
        self,
        seat_info: SeatInfo,
        seat_seqs: list[str],
        actor: CatalogActor,
    ) -> SeatInfo:
        try:
            await self._authorize(seat_info.perf_id, actor)
            return await self.create_seat_configuration(seat_info, seat_seqs)
        except BaseException:
            await self.repository.rollback()
            raise

    async def update_price(
        self,
        perf_id: int,
        seat_id: int,
        price: int,
        actor: CatalogActor,
    ) -> SeatInfo:
        try:
            await self._authorize(perf_id, actor)
            current = await self.get_seat_info(seat_id)
            if current.perf_id != perf_id:
                raise NotFoundException(
                    "해당 회차의 좌석 등급을 찾을 수 없습니다.",
                    error_code="SEAT_INFO_NOT_FOUND",
                )
            return await self.save_seat_info(replace(current, price=price))
        except BaseException:
            await self.repository.rollback()
            raise


class PerformanceSeatService:
    def __init__(
        self,
        repository: PerformanceSeatRepository,
        seat_info_repository: SeatInfoRepository,
    ) -> None:
        self.repository = repository
        self.seat_info_repository = seat_info_repository

    async def _require_performance(self, perf_id: int) -> None:
        if not await self.seat_info_repository.performance_exists(perf_id):
            raise NotFoundException(
                "공연 회차를 찾을 수 없습니다.", error_code="PERFORMANCE_NOT_FOUND"
            )

    async def list_performance_seats(self, perf_id: int) -> list[dict[str, object]]:
        await self._require_performance(perf_id)
        return await self.repository.list_performance_seats(perf_id)

    async def get_seat_info(self, perf_id: int, seat_id: int) -> dict[str, object]:
        grade = await self.seat_info_repository.get_seat_info_view(perf_id, seat_id)
        if grade is None:
            raise NotFoundException(
                "해당 회차의 좌석 등급을 찾을 수 없습니다.",
                error_code="SEAT_INFO_NOT_FOUND",
            )
        return grade

    async def get_performance_seat(
        self, perf_id: int, seat_seq: str
    ) -> dict[str, object]:
        await self._require_performance(perf_id)
        try:
            seat = await self.repository.get_performance_seat(perf_id, seat_seq)
        except SeatLookupConflictError as exc:
            raise SharedException(
                "좌석 정보를 확인할 수 없습니다.",
                status_code=500,
                error_code="SEAT_LOOKUP_INTEGRITY_ERROR",
            ) from exc
        if seat is None:
            raise NotFoundException(
                "해당 회차의 좌석을 찾을 수 없습니다.", error_code="SEAT_NOT_FOUND"
            )
        return seat

    async def get_reservation_seats(
        self, reserv_id: int, user_id: int
    ) -> dict[str, object]:
        try:
            reservation = await self.repository.get_owned_reservation_seats(
                reserv_id, user_id
            )
        except SeatLookupConflictError as exc:
            raise SharedException(
                "예매 좌석 정보를 확인할 수 없습니다.",
                status_code=500,
                error_code="RESERVATION_SEAT_INTEGRITY_ERROR",
            ) from exc
        if reservation is None:
            raise NotFoundException(
                "예매 좌석을 찾을 수 없습니다.", error_code="RESERVATION_NOT_FOUND"
            )
        return reservation
