from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    String,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    CheckConstraint,
    func,
    text,
)

from sqlalchemy.orm import Mapped, mapped_column

from asyncticket.shared.core.models import Base

## 회원 테이블
class UserModel(Base):
    __tablename__ = "users"

    __table_args__ = (
        CheckConstraint(
            "role IN ('ADMIN', 'SELLER', 'BUYER')",
            name="ck_users_role",
        ),
    )

    # 회원 고유 ID
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        primary_key=True,
    )

    # 이메일
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )

    # 비밀번호 해시
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # 회원 이름
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # 회원 권한
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'BUYER'"),
    )

    # 전화번호
    phone_number: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    # 생년월일
    birth: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    # 기본 주소
    address: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # 상세 주소
    address_detail: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # 우편번호
    post_no: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # 가입일시
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # 수정일시
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=func.now(),
    )

    # 탈퇴일시
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )



## blacklist_token 테이블
class BlacklistModel(Base):
    __tablename__ = "blacklist"

    black_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id"),
        nullable=False,
    )

    jti_token: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        unique=True,
    )

    expired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        server_default=func.now(),
    )