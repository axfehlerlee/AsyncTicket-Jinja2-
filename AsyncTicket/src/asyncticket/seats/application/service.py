from asyncticket.seats.domain.repository import SeatInfoRepository
from asyncticket.seats.domain.seat_info import SeatInfo


class SeatInfoService:
    def __init__(self, repository: SeatInfoRepository):
        self.repository = repository

    async def get_seat_info(self, seat_id: int) -> SeatInfo | None:
        return await self.repository.get_seat_info(seat_id)

    async def list_seat_infos(self, perf_id: int) -> list[SeatInfo]:
        return await self.repository.list_seat_infos(perf_id)
