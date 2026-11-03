
from asyncticket.venues.domain.repository import VenueRepository
from asyncticket.venues.domain.venue import Venue

class VenueService:
    def __init__(self, repository: VenueRepository):
        self.repo = repository

    async def create_venue(self, name: str, address: str, address_detail: str, post_no: str) -> Venue:
        if await self.repo.find_by_post_no(None, post_no):
            raise ValueError("이미 사용중인 공연장입니다.")

        venue = Venue.create(name = name, address = address, address_detail = address_detail, post_no = post_no)

        return await self.repo.save(venue)

    async def update_venue(
        self,
        venues_id: int,
        name: str,
        address: str,
        address_detail: str,
        post_no: str,
    ) -> Venue:
        venue = await self.repo.find_by_id(venues_id)

        if venue is None:
            raise ValueError("수정할 공연장이 없습니다.")

        if await self.repo.find_by_post_no(venues_id, post_no):
            raise ValueError("이미 사용중인 공연장입니다.")

        venue.update_info(
            name=name,
            address=address,
            address_detail=address_detail,
            post_no=post_no,
        )

        return await self.repo.save(venue)


    async def get_venue(self, venues_id: int) -> Venue | None:
        return await self.repo.find_by_id(venues_id)

    async def get_list_venue(self, name: str, address: str, page: int, page_size: int) -> list[Venue]:
        return await self.repo.find_by_filters(name, address, page, page_size)

