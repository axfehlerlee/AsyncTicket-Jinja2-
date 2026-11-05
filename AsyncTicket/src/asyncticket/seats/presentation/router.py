from typing import Annotated

from fastapi import APIRouter, Depends, Path, Response

from asyncticket.seats.application.service import PerformanceSeatService, SeatInfoService
from asyncticket.seats.domain.seat_info import SeatInfo
from asyncticket.wiring.seats import provide_seat_info_service
from asyncticket.wiring.performance_seats import provide_performance_seat_service
from asyncticket.seats.presentation.schemas import (
    ReservationSeatListResponse, SeatConfigurationRequest, SeatInfoResponse,
    SeatListResponse, SeatPriceUpdateRequest, SeatResponse,
)
from asyncticket.shared.core.schemas import APIResponse
from asyncticket.shared.domain.catalog import CatalogActor
from asyncticket.shared.presentation.catalog_auth import get_current_catalog_actor

router = APIRouter(prefix="/v1", tags=["좌석"], responses={
    code: {"model": APIResponse[None]} for code in (401, 403, 404, 409, 422, 500, 503)
})
PositiveId = Annotated[int, Path(gt=0, le=9223372036854775807)]
SeatSeq = Annotated[str, Path(min_length=1, max_length=255)]
PerformanceService = Annotated[PerformanceSeatService, Depends(provide_performance_seat_service)]
InfoService = Annotated[SeatInfoService, Depends(provide_seat_info_service)]
CurrentActor = Annotated[CatalogActor, Depends(get_current_catalog_actor)]


@router.get("/performances/{perf_id}/seats", response_model=APIResponse[SeatListResponse])
async def list_seats(perf_id: PositiveId, service: PerformanceService):
    seats = await service.list_performance_seats(perf_id)
    return APIResponse[SeatListResponse].ok(data=SeatListResponse(
        perf_id=perf_id, items=[SeatResponse.model_validate(seat) for seat in seats],
    ))


@router.get("/performances/{perf_id}/seats/{seat_seq}", response_model=APIResponse[SeatResponse])
async def get_seat(perf_id: PositiveId, seat_seq: SeatSeq, service: PerformanceService):
    seat = await service.get_performance_seat(perf_id, seat_seq)
    return APIResponse[SeatResponse].ok(data=SeatResponse.model_validate(seat))


@router.get("/reservations/{reserv_id}/seats", response_model=APIResponse[ReservationSeatListResponse])
async def get_owned_seats(reserv_id: PositiveId, service: PerformanceService, actor: CurrentActor):
    reservation = await service.get_reservation_seats(reserv_id, actor.user_id)
    return APIResponse[ReservationSeatListResponse].ok(
        data=ReservationSeatListResponse.model_validate(reservation),
    )


@router.post("/performances/{perf_id}/seat-infos", status_code=201, response_model=APIResponse[SeatInfoResponse])
async def create_configuration(
    perf_id: PositiveId, body: SeatConfigurationRequest, response: Response,
    service: InfoService, actor: CurrentActor,
):
    saved = await service.create(SeatInfo.create(
        perf_id=perf_id, name=body.name, total_seat=body.total_seat, price=body.price,
    ), body.seat_seqs, actor)
    response.headers["Location"] = f"/v1/performances/{perf_id}/seat-infos/{saved.seat_id}"
    return APIResponse[SeatInfoResponse].ok(data=SeatInfoResponse.model_validate(saved))


@router.get("/performances/{perf_id}/seat-infos/{seat_id}", response_model=APIResponse[SeatInfoResponse])
async def get_grade(perf_id: PositiveId, seat_id: PositiveId, service: PerformanceService):
    grade = await service.get_seat_info(perf_id, seat_id)
    return APIResponse[SeatInfoResponse].ok(data=SeatInfoResponse.model_validate(grade))


@router.patch("/performances/{perf_id}/seat-infos/{seat_id}", response_model=APIResponse[SeatInfoResponse])
async def update_price(
    perf_id: PositiveId, seat_id: PositiveId, body: SeatPriceUpdateRequest,
    service: InfoService, actor: CurrentActor,
):
    grade = await service.update_price(perf_id, seat_id, body.price, actor)
    return APIResponse[SeatInfoResponse].ok(data=SeatInfoResponse.model_validate(grade))
