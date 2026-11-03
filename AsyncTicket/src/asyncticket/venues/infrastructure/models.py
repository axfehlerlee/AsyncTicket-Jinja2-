from sqlalchemy import String, BigInteger, Identity
from sqlalchemy.orm import Mapped, mapped_column, relationship
from asyncticket.shared.core.models import Base
from typing import List
from asyncticket.venues.domain.venue import Venue

class VenueModel(Base):
    __tablename__ = "venues"

    venues_id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    address_detail: Mapped[str] = mapped_column(String(255), nullable=True)
    post_no: Mapped[str] = mapped_column(String(20), nullable=True)

    def to_venue(self) -> Venue:
        return Venue(self.venues_id, self.name, self.address, self.address_detail, self.post_no)