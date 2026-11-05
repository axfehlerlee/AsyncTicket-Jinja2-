from sqlalchemy import BigInteger, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from asyncticket.seats.domain.performanc_seat import PerformanceSeat
from asyncticket.seats.domain.seat_info import SeatInfo
from asyncticket.shared.core.models import Base


class SeatsInfoModel(Base):
    __tablename__ = "seats_info"

    seat_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True,
    )
    perf_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("performances.perf_id"), nullable=False,
    )
    # 기존 ERD의 nullable 컬럼은 유지한다. 미설정 행은 SeatInfo로 변환할 수 없다.
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    total_seat: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def to_seat_info(self) -> SeatInfo:
        if self.name is None:
            raise ValueError("좌석 등급명은 공백이 아닌 1~255자여야 합니다.")
        if self.total_seat is None:
            raise ValueError("좌석 수는 1 이상이어야 합니다.")
        if self.price is None:
            raise ValueError("가격은 50000 이상이어야 합니다.")
        return SeatInfo(
            seat_id=self.seat_id, perf_id=self.perf_id, name=self.name,
            total_seat=self.total_seat, price=self.price,
        )


class PerformanceSeats(Base):
    __tablename__ = "performance_seats"

    perf_seat_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True,
    )
    seat_id2: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("seats_info.seat_id"), nullable=False,
    )
    reserv_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("reservations.reserv_id"), nullable=True,
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    seat_seq: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def to_performance_seat(self) -> PerformanceSeat:
        if self.seat_seq is None:
            raise ValueError("좌석명은 공백이 아닌 1~255자여야 합니다.")
        return PerformanceSeat(
            perf_seat_id=self.perf_seat_id, seat_id=self.seat_id2,
            reserv_id=self.reserv_id, status=self.status, seat_seq=self.seat_seq,
        )
