import re

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum
from AsyncTicket.users.domain.service import PasswordHasher
from shared.core.exceptions import BadRequestException, ForbiddenException, ValidationException



## 회원권한 정의

class UserRole(str,Enum):
    ADMIN="ADMIN"
    SELLER="SELLER"
    BUYER="BUYER"

## 도메인 예외

class UserDomainError(ValueError):
    pass

## 검증규칙

EMAIL_PATTERN = re.compile(
    r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
)

PASSWORD_PATTERN = re.compile(
    r"^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]{8,128}$"
)

#USER 도메인 엔티티

@dataclass
class User:

    #회원정보
    user_id: int | None
    email: str
    name: str
    password_hash: str
    role: UserRole
    phone_number: str

    birth: date | None=None
    address: str | None=None
    address_detail: str | None=None
    post_no: str | None=None

    created_at: datetime | None=None
    updated_at: datetime | None=None
    deleted_at: datetime | None=None

    # 회원정보 검증
    def __post_init__(self) -> None:

        self.validate_email(self.email)
        self.validate_name(self.name)

      
    # 신규 회원 생성
    @classmethod
    def create(
        cls,
        email: str,
        name: str,
        raw_password: str,
        phone_number: str,
        hasher: PasswordHasher,
        birth: date,
        address: str | None=None,
        address_detail: str | None=None,
        post_no: str | None=None,
    ) -> "User":

        # 비밀번호 규칙 검증
        cls.validate_password(raw_password)

        # 비밀번호 해싱
        password_hash = hasher.hash(raw_password)

        # 신규 회원 객체
        return cls(
            user_id=None,
            email=email.strip().lower(),
            name=name.strip(),
            password_hash=password_hash,
            role=UserRole.BUYER,
            phone_number=phone_number,
            birth=birth,
            address=address,
            address_detail=address_detail,
            post_no=post_no,
            created_at=datetime.now(timezone.utc),
        )

    def change_password(
            self,
            old_password: str,
            new_password: str,
            hasher: PasswordHasher,
    ) -> None:
        ##비밀번호 변경
        if not hasher.verify(old_password, self.password_hash):
            raise BadRequestException(
                message="기존 비밀번호가 일치하지 않습니다.",
                error_code="INVALID_OLD_PASSWORD",
            )

        if old_password == new_password:
            raise BadRequestException(
                message="기존 비밀번호와 동일한 비밀번호로 변경할 수 없습니다.",
                error_code="SAME_PASSWORD",
            )

        self._validate_password(new_password)

        self.password_hash = hasher.hash(new_password)
        self.modified_at = datetime.now(timezone.utc)
    # 이메일 검증
    @staticmethod
    def validate_email(email: str) -> None:
        if not EMAIL_PATTERN.fullmatch(email):
            raise UserDomainError(
                "이메일 형식이 올바르지 않습니다"
            )
    # 이름 검증
    @staticmethod
    def validate_name(name: str) -> None:
        if not 2 <= len(name.strip()) <=20:
            raise UserDomainError(
                "이름은 2자 이상 20자 이하로 입력해야 합니다"
            )   
    # 비밀번호 검증
    @staticmethod
    def validate_password(password: str) -> None:
        if len(password.encode("utf-8"))>72:
            raise UserDomainError(
                "비밀번호는 72바이트를 초과할 수 없습니다"
            )
        if not PASSWORD_PATTERN.fullmatch(password):
            raise UserDomainError(
                "비밀번호는 8~128자 영문, 숫자, 특수문자를 포함해야 합니다"
            )
    