from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from asyncticket.seats.domain.repository import SeatInfoRepository
from asyncticket.seats.domain.seat_info import SeatInfo
from asyncticket.seats.infrastructure.models import SeatsInfoModel


class SqlAlchemySeatInfoRepository(SeatInfoRepository):
    def __init__(self, session: AsyncSession):
        self.session = session


    async def get_seat_info(self, seat_id: int) -> SeatInfo | None:
        seat_info = await self.session.get(SeatsInfoModel, seat_id)
        return self._to_seat_info(seat_info) if seat_info is not None else None


    async def list_seat_infos(self, perf_id: int) -> list[SeatInfo]:
        stmt = (
            select(SeatsInfoModel)
            .where(SeatsInfoModel.perf_id == perf_id)
            .order_by(SeatsInfoModel.seat_id)
        )
        result = await self.session.scalars(stmt)
        return [self._to_seat_info(item) for item in result.all()]


    @staticmethod
    def _to_seat_info(model: SeatsInfoModel) -> SeatInfo:
        return SeatInfo(
            seat_id=model.seat_id,
            perf_id=model.perf_id,
            name=model.name,
            total_seat=model.total_seat,
            price=model.price,
        )
