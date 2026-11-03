from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import BigInteger, Integer, Numeric, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from asyncticket.shared.core.models import Base # 모든 테이블의 부모


class Reservation(Base):
    """예매"""

    # DB에 만들어질 실제 테이블 이름
    __tablename__ = "reservations"

    # Mapped[파이썬 타입] = mapped_column(DB 타입, 옵션들)
    reserv_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True # DB가 알아서 PK 번호를 1씩 증가
    )

    order_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    # FK (users.user_id)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id"),
        nullable=False,
        index=True
    )

    # FK (performances.perf_id)
    perf_id: Mapped[int] = mapped_column(
        ForeignKey("performances.perf_id"),
        nullable=False,
        index=True
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Optianal 기능(| 파이프라인)
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=datetime.now(timezone.utc))

    canceled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True)


# class ReservationItem(Base):
#     """예매 상품"""

#     __tablename__ = "reservation_items"

# # 고민거리 
# #   1) 예매상품이란 테이블은 erd에 없는데.. 새로 만들어될지?, 
# #   2) 아니면 performance_seats 테이블을 예매에서 따로 관리를 하는 것인지??
# #       - 2번의 경우 seats/infrastucture models.py에 구성된 performance_seats class는 제외해야 오류가 나지 않음

#     perf_seat_id: Mapped[int] = mapped_column(
#         primary_key=True,
#         autoincrement=True
#     )

#     # FK (reservations.reserv_id)
#     reserv_id: Mapped[int] = mapped_column(
#         ForeignKey("reservations.reserv_id"),
#         nullable=False,
#         index=True
#     )

#     # FK (seats_info.seat_id)
#     seat_id2: Mapped[int] = mapped_column(
#         ForeignKey("seats_info.seat_id"),
#         nullable=False,
#         index=True
#     )

#     status: Mapped[str] = mapped_column(
#         String(30),
#         nullable=False
#     )

#     seat_seq: Mapped[str] = mapped_column(
#         String(255),
#         nullable=True # 좌석명 null 가능
#     )

