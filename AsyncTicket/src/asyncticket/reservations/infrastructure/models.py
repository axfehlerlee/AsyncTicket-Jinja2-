from datetime import datetime, timezone
from sqlalchemy import BigInteger, Integer, Numeric, Decimal, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
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

    # 관계설정 필요 (users.user_id)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False
    )

    # 관계설정 필요 (performances.perf_id)
    perf_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False
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
        default=datetime.now(timezone.utc),
        nullable=False)


    # Optianal 기능(| 파이프라인)
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=datetime.now(timezone.utc))

    canceled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True)