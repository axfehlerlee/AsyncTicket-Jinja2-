from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from asyncticket.shared.core.models import Base


class Payment(Base):
    __tablename__ = "payments"

    pay_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    reserv_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("reservations.reserv_id"), nullable=False, index=True
    )
    transaction_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    method: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)