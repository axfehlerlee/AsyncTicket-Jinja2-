from sqlalchemy import String, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from asyncticket.shared.core.models import Base
from typing import List

class VenuesModel(Base):
    __tablename__ = "venues"

    venues_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    address_detail: Mapped[str] = mapped_column(String(255), nullable=True)
    post_no: Mapped[str] = mapped_column(String(20), nullable=True)

    shows: Mapped[List["Shows"]] = relationship("Shows", back_populates="venues")