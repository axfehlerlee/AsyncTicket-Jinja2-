"""표현 계층: 공연회차 API 5개의 HTTP 입력·출력을 담당한다."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response

from asyncticket.shared.presentation.catalog_auth import get_current_catalog_actor
from asyncticket.performances.presentation.dependencies import provide_performance_service
from asyncticket.performances.application.service import (
    PERFORMANCE_DATE_MAX, PERFORMANCE_DATE_MIN, PerformanceApplicationService,
)
from asyncticket.performances.presentation.schemas import (
    PerformanceCreateRequest, PerformanceListResponse, PerformanceResponse,
    PerformanceUpdateRequest,
)
from asyncticket.shared.domain.catalog import CatalogActor
from asyncticket.shared.presentation.catalog_schemas import IsoDate
from asyncticket.shared.core.schemas import APIResponse

ERROR_RESPONSES = {code: {"model": APIResponse[None]} for code in (401, 403, 404, 409, 422, 500, 503)}
router = APIRouter(prefix="/v1", tags=["공연 회차"], responses=ERROR_RESPONSES)
PerformanceService = Annotated[PerformanceApplicationService, Depends(provide_performance_service)]
Actor = Annotated[CatalogActor, Depends(get_current_catalog_actor)]
ShowId = Annotated[int, Path(gt=0, le=9223372036854775807, description="공연 ID")]
PerformanceId = Annotated[int, Path(gt=0, le=9223372036854775807, description="공연 회차 ID")]


@router.get(
    "/shows/{show_id}/performances", response_model=APIResponse[PerformanceListResponse],
    summary="공연별 회차 목록 조회",
)
async def get_list_performance(
    show_id: ShowId, service: PerformanceService,
    date: Annotated[IsoDate | None, Query(
        ge=PERFORMANCE_DATE_MIN, le=PERFORMANCE_DATE_MAX,
        description="공연 시작일 (YYYY-MM-DD, Asia/Seoul, 0001-01-02~9999-12-30)",
    )] = None,
) -> APIResponse[PerformanceListResponse]:
    items = await service.find_all(show_id, date)
    return APIResponse[PerformanceListResponse].ok(data=PerformanceListResponse(
        items=[PerformanceResponse.model_validate(item) for item in items]
    ))


@router.get(
    "/performances/{perf_id}", response_model=APIResponse[PerformanceResponse], summary="회차 상세 조회",
)
async def get_detail_performance(
    perf_id: PerformanceId, service: PerformanceService,
) -> APIResponse[PerformanceResponse]:
    return APIResponse[PerformanceResponse].ok(
        data=PerformanceResponse.model_validate(await service.find_by_id(perf_id))
    )


@router.post(
    "/shows/{show_id}/performances", status_code=201,
    response_model=APIResponse[PerformanceResponse], summary="회차 등록",
)
async def create_performance(
    show_id: ShowId, body: PerformanceCreateRequest, response: Response,
    actor: Actor, service: PerformanceService,
) -> APIResponse[PerformanceResponse]:
    performance = await service.create(show_id, body.model_dump(), actor)
    response.headers["Location"] = f"/v1/performances/{performance.perf_id}"
    return APIResponse[PerformanceResponse].ok(data=PerformanceResponse.model_validate(performance))


@router.patch(
    "/performances/{perf_id}", response_model=APIResponse[PerformanceResponse], summary="회차 수정",
)
async def update_performance(
    perf_id: PerformanceId, body: PerformanceUpdateRequest,
    actor: Actor, service: PerformanceService,
) -> APIResponse[PerformanceResponse]:
    return APIResponse[PerformanceResponse].ok(data=PerformanceResponse.model_validate(
        await service.update(perf_id, body.model_dump(exclude_unset=True), actor)
    ))


@router.delete(
    "/performances/{perf_id}", status_code=204, response_class=Response, summary="회차 삭제",
)
async def delete_performance(
    perf_id: PerformanceId, actor: Actor, service: PerformanceService,
) -> Response:
    await service.delete(perf_id, actor)
    return Response(status_code=204)
