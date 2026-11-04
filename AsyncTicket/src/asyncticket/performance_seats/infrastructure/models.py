"""20261029 AsyncTicket 스냅샷 기준 좌석 ORM 모델."""

from sqlalchemy import BigInteger, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from asyncticket.shared.core.models import Base


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from asyncticket.seats.infrastructure.models import SeatsInfoModel


class PerformanceSeats(Base):
    __tablename__ = "performance_seats"

    perf_seat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # 예매 전에는 비워두고, 예매 생성 후 같은 트랜잭션에서 연결한다.
    reserv_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("reservations.reserv_id"), nullable=True
    )
    seat_id2: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("seats_info.seat_id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    seat_seq: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # FK에 해당하는 객체 접근을 연결한다. 삭제 정책을 임의로 추가하지 않는다.
    seat_info: Mapped["SeatsInfoModel"] = relationship(back_populates="performance_seats")
