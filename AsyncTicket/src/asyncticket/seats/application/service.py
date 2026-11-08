# <응용 서비스 - 좌석 처리 순서 조율>
# - 구성·가격 변경은 이 서비스가 commit/rollback한다. 예매 연결·해제는 예매 호출부가 트랜잭션을 맡는다.

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
    ValidationException,
)
from asyncticket.shared.domain.catalog import CatalogActor, CatalogPolicy


class SeatReservationConflictError(ConflictException):
    """기존 호출자가 구분하는 예외 이름을 유지하며 팀 공통 409 처리에 연결한다."""
    def __init__(self, message: str):
        super().__init__(message, error_code="SEAT_RESERVATION_CONFLICT")


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

    # 1) 좌석 등급 조회, 없으면 404
    async def get_seat_info(self, seat_id: int) -> SeatInfo:
        seat_info = await self.repository.get_seat_info(seat_id)
        if seat_info is None:
            raise NotFoundException(
                "좌석 등급을 찾을 수 없습니다.", error_code="SEAT_INFO_NOT_FOUND"
            )
        return seat_info

    # 2) 기존 등급의 가격만 저장·확정
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

    # 3) 등급 잔여 수량으로 요청 가능 여부 검사
    async def check_seat_availability(
        self,
        seat_id: int,
        quantity: int,
        occupied_count: int,
    ) -> None:
        seat_info = await self.get_seat_info(seat_id)
        seat_info.require_capacity(quantity, occupied_count)

    # 4) 기존 호출부용 수량 검사 진입점
    async def check_capacity(
        self,
        seat_id: int,
        quantity: int,
        occupied_count: int,
    ) -> None:
        await self.check_seat_availability(seat_id, quantity, occupied_count)

    # 5) 등급 저장 → 개별 좌석 저장 → 함께 확정
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

    # 6) 판매자·소유자·판매 시작 시각 검사
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

    # 7) 권한 확인 후 좌석 구성 생성
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

    # 8) 권한 확인 후 기존 등급 가격 수정
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

    # 1) 회차 존재 여부 검사
    async def _require_performance(self, perf_id: int) -> None:
        if not await self.seat_info_repository.performance_exists(perf_id):
            raise NotFoundException(
                "공연 회차를 찾을 수 없습니다.", error_code="PERFORMANCE_NOT_FOUND"
            )

    # 2) 회차 확인 후 좌석 목록 조회
    async def list_performance_seats(self, perf_id: int) -> list[dict[str, object]]:
        await self._require_performance(perf_id)
        return await self.repository.list_performance_seats(perf_id)

    # 3) 좌석 등급 조회, 없으면 404
    async def get_seat_info(self, perf_id: int, seat_id: int) -> dict[str, object]:
        grade = await self.seat_info_repository.get_seat_info_view(perf_id, seat_id)
        if grade is None:
            raise NotFoundException(
                "해당 회차의 좌석 등급을 찾을 수 없습니다.",
                error_code="SEAT_INFO_NOT_FOUND",
            )
        return grade

    # 4) 좌석명으로 상세 조회, 중복 데이터는 서버 오류
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

    # 6) 본인 예매의 좌석 조회
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

    # 7) 같은 세션에서 발급받은 예매 ID로 좌석 연결
    async def assign_reservation(
        self, *, perf_id: int, perf_seat_id: int, reserv_id: int,
        expected_status: str, reserved_status: str,
    ) -> None:
        """예매와 같은 세션에서 호출한다. 상태값은 팀 합의 후 전달한다."""
        # reserv_id는 예매에서 받은 ID, 두 status는 연결 전후의 좌석 상태다.
        if min(perf_id, perf_seat_id, reserv_id) <= 0:
            raise ValidationException("회차·좌석·예매 번호는 양수여야 합니다.", error_code="INVALID_SEAT_RESERVATION_ID")
        if not expected_status or not reserved_status or expected_status == reserved_status:
            raise ValidationException("연결 전후의 서로 다른 좌석 상태가 필요합니다.", error_code="INVALID_SEAT_STATUS_TRANSITION")
        linked = await self.repository.assign_reservation(
            perf_id=perf_id, perf_seat_id=perf_seat_id, reserv_id=reserv_id,
            expected_status=expected_status, reserved_status=reserved_status,
        )
        if not linked:
            raise SeatReservationConflictError("좌석을 예매에 연결할 수 없습니다.")

    # 5) 예매에 사용할 개별 좌석 ID로 가격·상태 조회
    async def get_performance_seat_by_id(
        self, *, perf_id: int, perf_seat_id: int,
    ) -> dict[str, object]:
        """예매 내부 조회용. 가격은 DB의 int/None 값을 반환하며 상태나 트랜잭션을 바꾸지 않는다.

        조회 성공은 선점이 아니다. 연결 시 assign_reservation으로 조건을 다시 검사한다.
        """
        if any(type(value) is not int or not 0 < value <= 9223372036854775807
               for value in (perf_id, perf_seat_id)):
            raise ValidationException("회차·좌석 번호는 유효한 양수여야 합니다.", error_code="INVALID_SEAT_RESERVATION_ID")
        await self._require_performance(perf_id)
        seat = await self.repository.get_performance_seat_by_id(perf_id, perf_seat_id)
        if seat is None:
            raise NotFoundException(
                "해당 회차의 좌석을 찾을 수 없습니다.", error_code="SEAT_NOT_FOUND",
            )
        return seat
