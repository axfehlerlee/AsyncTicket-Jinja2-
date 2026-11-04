"""좌석 응답의 안쪽 데이터. 공통 success/code 등은 APIResponse가 담당한다."""
from pydantic import BaseModel, ConfigDict, Field


class SeatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    perf_seat_id: int = Field(description="회차별 개별 좌석 ID")
    seat_id: int = Field(description="좌석 등급 ID")
    perf_id: int
    grade: str | None
    seat_seq: str | None
    price: int | None
    # 상태값 해석을 임의로 정하지 않고 DB의 판매 상태를 그대로 응답한다.
    status: str


class SeatListResponse(BaseModel):
    perf_id: int
    items: list[SeatResponse]
