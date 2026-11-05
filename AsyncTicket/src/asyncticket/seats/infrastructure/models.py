"""20261029 AsyncTicket 스냅샷 기준 좌석 ORM 모델."""

from sqlalchemy import BigInteger, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from asyncticket.shared.core.models import Base


from typing import TYPE_CHECKING

from asyncticket.performance_seats.infrastructure.models import PerformanceSeats


class SeatsInfoModel(Base):
    __tablename__ = "seats_info"

    seat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    perf_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("performances.perf_id"), nullable=False
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Python 속성명도 ERD의 실제 컬럼명 total_seat과 맞춘다.
    total_seat: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # ERD의 가격 타입은 INT이므로 Numeric이 아닌 Integer를 사용한다.
    price: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 등급 정보 한 건에 연결된 회차별 좌석들을 역방향으로 조회한다.
    performance_seats: Mapped[list["PerformanceSeats"]] = relationship(
        back_populates="seat_info"
    )
