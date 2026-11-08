from sqlalchemy import (
    BigInteger,
    DateTime,
    Integer,
    Numeric,
    column,
    exists,
    select,
    table,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession

from asyncticket.seats.domain.performanc_seat import PerformanceSeat
from asyncticket.seats.domain.repository import (
    PerformanceSeatRepository,
    SeatInfoRepository,
    SeatLookupConflictError,
)
from asyncticket.seats.domain.seat_info import SeatInfo
from asyncticket.seats.infrastructure.models import PerformanceSeats, SeatsInfoModel

performances = table(
    "performances",
    column("perf_id", BigInteger),
    column("show_id", BigInteger),
    column("booking_opens_at", DateTime(timezone=True)),
)
shows = table("shows", column("show_id", BigInteger), column("user_id", BigInteger))
reservations = table(
    "reservations",
    column("reserv_id", BigInteger),
    column("user_id", BigInteger),
    column("perf_id", BigInteger),
    column("quantity", Integer),
    column("total_amount", Numeric(12, 2)),
)


class SqlAlchemySeatInfoRepository(SeatInfoRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_seat_info(self, seat_id: int) -> SeatInfo | None:
        stmt = (
            select(SeatsInfoModel)
            .where(
                SeatsInfoModel.seat_id == seat_id,
            )
            .execution_options(populate_existing=True)
        )
        model = await self.session.scalar(stmt)
        return model.to_seat_info() if model is not None else None

    async def save_seat_info(self, seat_info: SeatInfo) -> SeatInfo:
        if seat_info.seat_id is None:
            model = SeatsInfoModel(
                perf_id=seat_info.perf_id,
                name=seat_info.name,
                total_seat=seat_info.total_seat,
                price=seat_info.price,
            )
            self.session.add(model)
        else:
            stmt = select(SeatsInfoModel).where(
                SeatsInfoModel.seat_id == seat_info.seat_id
            )
            model = await self.session.scalar(stmt)
            if model is None:
                raise LookupError("저장할 좌석 등급이 없습니다.")
            if model.perf_id != seat_info.perf_id:
                raise ValueError("저장된 좌석 등급의 회차는 변경할 수 없습니다.")
            model.name = seat_info.name
            model.total_seat = seat_info.total_seat
            model.price = seat_info.price

        await self.session.flush()
        await self.session.refresh(model)
        return model.to_seat_info()

    async def grade_exists(self, perf_id: int, name: str) -> bool:
        stmt = select(
            exists().where(
                SeatsInfoModel.perf_id == perf_id,
                SeatsInfoModel.name == name,
            )
        )
        return bool(await self.session.scalar(stmt))

    async def lock_performance(self, perf_id: int) -> bool:
        stmt = (
            select(performances.c.perf_id)
            .where(
                performances.c.perf_id == perf_id,
            )
            .with_for_update()
        )
        return await self.session.scalar(stmt) is not None

    async def get_seat_info_view(
        self, perf_id: int, seat_id: int
    ) -> dict[str, object] | None:
        stmt = select(
            SeatsInfoModel.seat_id,
            SeatsInfoModel.perf_id,
            SeatsInfoModel.name,
            SeatsInfoModel.total_seat,
            SeatsInfoModel.price,
        ).where(SeatsInfoModel.perf_id == perf_id, SeatsInfoModel.seat_id == seat_id)
        result = await self.session.execute(stmt)
        row = result.mappings().one_or_none()
        return dict(row) if row is not None else None

    async def performance_exists(self, perf_id: int) -> bool:
        return bool(
            await self.session.scalar(
                select(exists().where(performances.c.perf_id == perf_id))
            )
        )

    async def get_management_context(self, perf_id: int) -> dict[str, object] | None:
        stmt = (
            select(shows.c.user_id.label("owner_id"), performances.c.booking_opens_at)
            .select_from(
                performances.join(shows, performances.c.show_id == shows.c.show_id)
            )
            .where(performances.c.perf_id == perf_id)
        )
        result = await self.session.execute(stmt)
        row = result.mappings().one_or_none()
        return dict(row) if row is not None else None

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()



class SqlAlchemyPerformanceSeatRepository(PerformanceSeatRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_many(self, seats: list[PerformanceSeat]) -> None:
        if any(seat.perf_seat_id is not None for seat in seats):
            raise ValueError("좌석 목록 저장은 신규 좌석만 지원합니다.")
        self.session.add_all(
            [
                PerformanceSeats(
                    seat_id2=seat.seat_id,
                    seat_seq=seat.seat_seq,
                    status=seat.status,
                    reserv_id=seat.reserv_id,
                )
                for seat in seats
            ]
        )
        await self.session.flush()

    async def names_exist(self, perf_id: int, seat_seqs: list[str]) -> bool:
        stmt = select(
            exists(
                select(PerformanceSeats.perf_seat_id)
                .join(
                    SeatsInfoModel, PerformanceSeats.seat_id2 == SeatsInfoModel.seat_id
                )
                .where(
                    SeatsInfoModel.perf_id == perf_id,
                    PerformanceSeats.seat_seq.in_(seat_seqs),
                )
            )
        )
        return bool(await self.session.scalar(stmt))

    @staticmethod
    def _seats():
        return select(
            PerformanceSeats.perf_seat_id,
            SeatsInfoModel.seat_id,
            SeatsInfoModel.perf_id,
            SeatsInfoModel.name.label("grade"),
            PerformanceSeats.seat_seq,
            SeatsInfoModel.price,
            PerformanceSeats.status,
        ).join(SeatsInfoModel, PerformanceSeats.seat_id2 == SeatsInfoModel.seat_id)

    async def list_performance_seats(self, perf_id: int) -> list[dict[str, object]]:
        stmt = (
            self._seats()
            .where(SeatsInfoModel.perf_id == perf_id)
            .order_by(PerformanceSeats.perf_seat_id)
        )
        result = await self.session.execute(stmt)
        return [dict(row) for row in result.mappings()]

    async def get_performance_seat(
        self, perf_id: int, seat_seq: str
    ) -> dict[str, object] | None:
        stmt = (
            self._seats()
            .where(
                SeatsInfoModel.perf_id == perf_id,
                PerformanceSeats.seat_seq == seat_seq,
            )
            .limit(2)
        )
        result = await self.session.execute(stmt)
        rows = result.mappings().all()
        if len(rows) > 1:
            raise SeatLookupConflictError("회차 안에서 좌석명이 중복됩니다.")
        return dict(rows[0]) if rows else None

    async def get_owned_reservation_seats(
        self,
        reserv_id: int,
        user_id: int,
    ) -> dict[str, object] | None:
        stmt = select(reservations).where(
            reservations.c.reserv_id == reserv_id,
            reservations.c.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        reservation = result.mappings().one_or_none()
        if reservation is None:
            return None
        result = await self.session.execute(
            self._seats()
            .where(PerformanceSeats.reserv_id == reserv_id)
            .order_by(PerformanceSeats.perf_seat_id)
        )
        items = [dict(row) for row in result.mappings()]
        if any(item["perf_id"] != reservation["perf_id"] for item in items):
            raise SeatLookupConflictError(
                "예매와 연결 좌석의 회차가 일치하지 않습니다."
            )
        return {
            "reserv_id": reserv_id,
            "quantity": reservation["quantity"],
            "purchase_price": reservation["total_amount"],
            "items": items,
        }

    async def assign_reservation(
        self,
        *,
        perf_id: int,
        perf_seat_id: int,
        reserv_id: int,
        expected_status: str,
        reserved_status: str,
    ) -> bool:
        # 예매 측에서 같은 세션으로 먼저 flush하고, 최종 commit도 맡는다.
        # 좌석의 회차·현재 상태·미연결 여부와 같은 회차의 예매 존재를 함께 검사한다.
        stmt = (
            update(PerformanceSeats)
            .where(
                PerformanceSeats.perf_seat_id == perf_seat_id,
                PerformanceSeats.reserv_id.is_(None),
                PerformanceSeats.status == expected_status,
                PerformanceSeats.seat_id2.in_(
                    select(SeatsInfoModel.seat_id).where(
                        SeatsInfoModel.perf_id == perf_id
                    )
                ),
                select(reservations.c.reserv_id)
                .where(
                    reservations.c.reserv_id == reserv_id,
                    reservations.c.perf_id == perf_id,
                )
                .exists(),
            )
            .values(
                reserv_id=reserv_id,
                status=reserved_status,
            )
            .returning(PerformanceSeats.perf_seat_id)
            .execution_options(synchronize_session=False)
        )
        return (await self.session.scalar(stmt)) is not None

    # 6) 회차·좌석 PK SELECT → 한 건 또는 None
    async def get_performance_seat_by_id(
        self, perf_id: int, perf_seat_id: int,
    ) -> dict[str, object] | None:
        result = await self.session.execute(self._seats().where(
            SeatsInfoModel.perf_id == perf_id,
            PerformanceSeats.perf_seat_id == perf_seat_id,
        ))
        row = result.mappings().one_or_none()
        return dict(row) if row else None
