"""좌석의 HTTP 입출력. 업무 실패 응답은 팀 공통 예외 처리기에 맡긴다."""
from typing import Annotated

from fastapi import APIRouter, Depends, Path

from asyncticket.seats.application.service import SeatService
from asyncticket.seats.presentation.dependencies import provide_seat_service
from asyncticket.seats.presentation.schemas import SeatListResponse, SeatResponse
from asyncticket.shared.core.schemas import APIResponse

router = APIRouter(
    prefix="/v1/performances", tags=["좌석"],
    responses={code: {"model": APIResponse[None]} for code in (404, 422, 500)},
)
SeatServiceDep = Annotated[SeatService, Depends(provide_seat_service)]


@router.get("/{perf_id}/seats", response_model=APIResponse[SeatListResponse])
async def list_performance_seats(
    perf_id: Annotated[int, Path(gt=0)], service: SeatServiceDep,
) -> APIResponse[SeatListResponse]:
    items = await service.list_performance_seats(perf_id)
    # 안쪽 좌석 필드는 기존 계약대로 두고, 팀 공통 data 칸에 목록을 담는다.
    return APIResponse[SeatListResponse].ok(
        data=SeatListResponse(
            perf_id=perf_id, items=[SeatResponse.model_validate(item) for item in items],
        ),
        message="회차별 좌석 조회에 성공했습니다.",
    )


@router.get("/{perf_id}/seats/{seat_seq}", response_model=APIResponse[SeatResponse])
async def get_performance_seat(
    perf_id: Annotated[int, Path(gt=0)],
    seat_seq: Annotated[str, Path(min_length=1, max_length=255)],
    service: SeatServiceDep,
) -> APIResponse[SeatResponse]:
    seat = await service.get_performance_seat(perf_id, seat_seq)
    # 예매 ID는 공개 조회 응답에 포함하지 않는다. 이 GET은 좌석을 선점하지 않는다.
    return APIResponse[SeatResponse].ok(
        data=SeatResponse.model_validate(seat), message="좌석 상세 조회에 성공했습니다.",
    )
