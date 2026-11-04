from datetime import datetime

from sqlalchemy import (
    DateTime,
    String,
)

from sqlalchemy.orm import Mapped, mapped_column

from asyncticket.shared.core.models import Base


class BlacklistModel(Base):
    __tablename__ = "blacklist"

  
    jti_token: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        primay_key=True,
    )

    expired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

