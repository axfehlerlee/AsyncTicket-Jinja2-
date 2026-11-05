from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

SeatName = Annotated[str, StringConstraints(min_length=1, max_length=255)]
SeatPrice = Annotated[int, Field(strict=True, ge=50000, le=2147483647)]


class SeatConfigurationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: SeatName
    total_seat: int = Field(strict=True, gt=0, le=2147483647)
    price: SeatPrice
    seat_seqs: list[SeatName]

    @model_validator(mode="after")
    def validate_names(self):
        if not self.name.strip() or any(not name.strip() for name in self.seat_seqs):
            raise ValueError("등급명과 좌석명은 공백일 수 없습니다.")
        if len(self.seat_seqs) != self.total_seat:
            raise ValueError("좌석명 개수와 등급 좌석 수가 일치해야 합니다.")
        if len(set(self.seat_seqs)) != len(self.seat_seqs):
            raise ValueError("중복된 좌석명이 있습니다.")
        return self


class SeatPriceUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    price: SeatPrice


class SeatInfoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    seat_id: int
    perf_id: int
    name: str | None
    total_seat: int | None
    price: int | None


class SeatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    perf_seat_id: int
    seat_id: int
    perf_id: int
    grade: str | None
    seat_seq: str | None
    price: int | None
    status: str


class SeatListResponse(BaseModel):
    perf_id: int
    items: list[SeatResponse]


class ReservationSeatListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    reserv_id: int
    quantity: int
    # 예매 전체의 구매 당시 금액이다. 좌석별 구매가로 복사하지 않는다.
    purchase_price: Decimal
    items: list[SeatResponse]
