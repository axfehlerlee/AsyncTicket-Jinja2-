"""이전 예매 좌석 상세 검토안에 따른 ORM 초안.

컬럼명은 10/29 담당 가이드, 타입과 NULL 허용 여부는 10/27 검토안을 따른다.
최신 ERD에는 별도 테이블이 없으므로 공통 init_models()에는 자동 등록하지 않는다.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from asyncticket.shared.core.models import Base


class ReservationItem(Base):
    __tablename__ = "reservation_items"

    reserv_item_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )

    # 이전 검토안의 FK 이름을 현재 팀 모델의 실제 PK 이름에 맞춘다.
    reserv_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("reservations.reserv_id"), nullable=False
    )
    perf_seat_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("performance_seats.perf_seat_id"), nullable=False
    )

    # 구매 당시 금액을 정확히 보존하기 위해 float 대신 Decimal/Numeric을 쓴다.
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    canceled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
