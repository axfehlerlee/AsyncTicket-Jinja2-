"""표현 계층: 공연 API 5개의 HTTP 입력·출력을 담당한다."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response

from asyncticket.shared.presentation.catalog_auth import get_current_catalog_actor
from asyncticket.shows.presentation.dependencies import provide_show_service
from asyncticket.shared.domain.catalog import CatalogActor
from asyncticket.shared.core.schemas import APIResponse
from asyncticket.shows.application.service import ShowApplicationService
from asyncticket.shows.domain.show import ShowQuery
from asyncticket.shows.presentation.schemas import (
    ShowCreateRequest, ShowListResponse, ShowResponse, ShowUpdateRequest,
)

ERROR_RESPONSES = {code: {"model": APIResponse[None]} for code in (401, 403, 404, 409, 422, 500, 503)}
router = APIRouter(prefix="/v1/shows", tags=["공연"], responses=ERROR_RESPONSES)
ShowService = Annotated[ShowApplicationService, Depends(provide_show_service)]
Actor = Annotated[CatalogActor, Depends(get_current_catalog_actor)]
ShowId = Annotated[int, Path(gt=0, le=9223372036854775807, description="공연 ID")]


@router.get("", response_model=APIResponse[ShowListResponse], summary="공연 목록 조회")
async def get_list_show(
    service: ShowService,
    page: Annotated[int, Query(ge=1, le=2147483647, description="페이지")] = 1,
    size: Annotated[int, Query(ge=1, le=100, description="페이지 크기")] = 20,
    keyword: Annotated[str | None, Query(max_length=255, description="공연명 검색")] = None,
    type: Annotated[str | None, Query(max_length=50, description="공연 분류")] = None,
    venues_id: Annotated[int | None, Query(gt=0, le=9223372036854775807, description="공연장 ID")] = None,
) -> APIResponse[ShowListResponse]:
    items, total = await service.find_all(ShowQuery(page, size, keyword, type, venues_id))
    return APIResponse[ShowListResponse].ok(data=ShowListResponse(
        items=[ShowResponse.model_validate(item) for item in items],
        page=page, size=size, total=total,
    ))


@router.get("/{show_id}", response_model=APIResponse[ShowResponse], summary="공연 상세 조회")
async def get_detail_show(show_id: ShowId, service: ShowService) -> APIResponse[ShowResponse]:
    return APIResponse[ShowResponse].ok(data=ShowResponse.model_validate(await service.find_by_id(show_id)))


@router.post("", status_code=201, response_model=APIResponse[ShowResponse], summary="공연 등록")
async def create_show(
    body: ShowCreateRequest, response: Response, actor: Actor, service: ShowService,
) -> APIResponse[ShowResponse]:
    # 라우터는 SQL을 실행하지 않고 스키마를 서비스 입력으로 바꾼다.
    show = await service.create(body.model_dump(), actor)
    response.headers["Location"] = f"/v1/shows/{show.show_id}"
    return APIResponse[ShowResponse].ok(data=ShowResponse.model_validate(show))


@router.patch("/{show_id}", response_model=APIResponse[ShowResponse], summary="공연 수정")
async def update_show(
    show_id: ShowId, body: ShowUpdateRequest, actor: Actor, service: ShowService,
) -> APIResponse[ShowResponse]:
    # exclude_unset 덕분에 '생략'과 'null로 비우기'를 구분할 수 있다.
    return APIResponse[ShowResponse].ok(data=ShowResponse.model_validate(
        await service.update(show_id, body.model_dump(exclude_unset=True), actor)
    ))


@router.delete("/{show_id}", status_code=204, response_class=Response, summary="공연 삭제")
async def delete_show(show_id: ShowId, actor: Actor, service: ShowService) -> Response:
    await service.delete(show_id, actor)
    return Response(status_code=204)
