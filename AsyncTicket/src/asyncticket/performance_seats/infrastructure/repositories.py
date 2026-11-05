from sqlalchemy import BigInteger, column, select, table, update
from sqlalchemy.exc import MultipleResultsFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from asyncticket.performance_seats.domain.repository import PerformanceSeatRepository, SeatLookupConflictError
from asyncticket.performance_seats.domain.performance_seat import PerformanceSeat
from asyncticket.performance_seats.infrastructure.models import PerformanceSeats
from asyncticket.seats.infrastructure.models import SeatsInfoModel

performances = table("performances", column("perf_id", BigInteger))
reservations = table("reservations", column("reserv_id", BigInteger), column("perf_id", BigInteger))


class SqlAlchemyPerformanceSeatRepository(PerformanceSeatRepository):
    def __init__(self, session: AsyncSession):
        self.session = session


    async def performance_exists(self, perf_id: int) -> bool:
        stmt = select(performances.c.perf_id).where(
            performances.c.perf_id == perf_id
        )
        return await self.session.scalar(stmt) is not None


    async def list_performance_seats(self, perf_id: int) -> list[PerformanceSeat]:
        stmt = (
            select(PerformanceSeats)
            .join(PerformanceSeats.seat_info)
            .options(joinedload(PerformanceSeats.seat_info))
            .where(SeatsInfoModel.perf_id == perf_id)
            .order_by(PerformanceSeats.perf_seat_id)
        )
        # 관계를 함께 읽어 AsyncSession에서 뒤늦은 지연 로딩이 일어나지 않게 한다.
        result = await self.session.scalars(stmt)
        return [self._to_performance_seat(item) for item in result.all()]


    async def get_performance_seat(
        self, perf_id: int, seat_seq: str
    ) -> PerformanceSeat | None:
        stmt = (
            select(PerformanceSeats)
            .join(PerformanceSeats.seat_info)
            .options(joinedload(PerformanceSeats.seat_info))
            .where(
                SeatsInfoModel.perf_id == perf_id,
                PerformanceSeats.seat_seq == seat_seq,
            )
        )
        result = await self.session.scalars(stmt)
        try:
            # 좌석명 중복 정책이 미정이므로 첫 행을 임의로 선택하지 않는다.
            seat = result.one_or_none()
        except MultipleResultsFound as exc:
            raise SeatLookupConflictError("회차 안에 좌석명이 중복됩니다.") from exc
        return self._to_performance_seat(seat) if seat is not None else None


    async def assign_reservation(
        self, *, perf_id: int, perf_seat_id: int, reserv_id: int,
        expected_status: str, reserved_status: str,
    ) -> bool:
        # 예매 생성 측에서 먼저 flush하여 reserv_id를 발급받아야 한다.
        # 회차·현재 상태·미연결 여부를 한 UPDATE의 조건으로 검사한다.
        stmt = (
            update(PerformanceSeats)
            .where(
                PerformanceSeats.perf_seat_id == perf_seat_id,
                PerformanceSeats.reserv_id.is_(None),
                PerformanceSeats.status == expected_status,
                PerformanceSeats.seat_id2.in_(
                    select(SeatsInfoModel.seat_id).where(SeatsInfoModel.perf_id == perf_id)
                ),
                select(reservations.c.reserv_id).where(
                    reservations.c.reserv_id == reserv_id,
                    reservations.c.perf_id == perf_id,
                ).exists(),
            )
            .values(reserv_id=reserv_id, status=reserved_status)
            .returning(PerformanceSeats.perf_seat_id)
            .execution_options(synchronize_session=False)
        )
        return (await self.session.scalar(stmt)) is not None


    @staticmethod
    def _to_performance_seat(model: PerformanceSeats) -> PerformanceSeat:
        return PerformanceSeat(
            perf_seat_id=model.perf_seat_id,
            seat_id=model.seat_id2,
            perf_id=model.seat_info.perf_id,
            grade=model.seat_info.name,
            seat_seq=model.seat_seq,
            price=model.seat_info.price,
            status=model.status,
        )
