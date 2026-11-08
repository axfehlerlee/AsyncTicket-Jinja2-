"""Jinja2 화면을 여는 주소를 등록한다."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from asyncticket.reservations.application.selection import (
    ReservationSelection,
    ReservationSelectionReader,
)
from asyncticket.shared.core.exceptions import ForbiddenException
from asyncticket.shared.core.schemas import APIResponse
from asyncticket.users.domain.users import User, UserRole
from asyncticket.wiring.auth import get_current_user
from asyncticket.wiring.reservation_selection import get_reservation_selection_reader

router = APIRouter(default_response_class=HTMLResponse, include_in_schema=False)
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


@router.get("/")
async def home(request: Request):
    return templates.TemplateResponse(request, "Home.html")


@router.get("/signup")
async def signup(request: Request):
    return templates.TemplateResponse(request, "signup.html")


@router.get("/login")
async def login(request: Request):
    return templates.TemplateResponse(request, "login.html")


@router.get("/me")
async def profile(request: Request):
    return templates.TemplateResponse(request, "profile.html")


@router.get("/venues")
async def venues(request: Request):
    return templates.TemplateResponse(request, "venues.html")


@router.get("/venues/{venue_id}")
async def venue(request: Request, venue_id: int):
    return templates.TemplateResponse(request, "venue.html", {"venue_id": venue_id})


@router.get("/shows")
async def shows(request: Request):
    return templates.TemplateResponse(request, "shows.html")


@router.get("/shows/{show_id}")
async def show(request: Request, show_id: int):
    return templates.TemplateResponse(request, "show.html", {"show_id": show_id})


@router.get("/performances/{performance_id}")
async def performance(request: Request, performance_id: int):
    return templates.TemplateResponse(
        request, "performance.html", {"performance_id": performance_id}
    )


@router.get("/manage/edit")
async def manage_edit(request: Request):
    return templates.TemplateResponse(request, "manage.html")


@router.get("/reservations")
async def reservations(request: Request):
    return templates.TemplateResponse(request, "reservations.html")


@router.get("/reservations/check", response_class=JSONResponse)
async def check_reservation_selection(
    response: Response,
    perf_id: Annotated[int, Query(gt=0, le=2**63 - 1)],
    perf_seat_id: Annotated[int, Query(gt=0, le=2**63 - 1)],
    user: Annotated[User, Depends(get_current_user)],
    reader: Annotated[ReservationSelectionReader, Depends(get_reservation_selection_reader)],
) -> APIResponse[ReservationSelection]:
    if user.role != UserRole.BUYER or user.user_id is None:
        raise ForbiddenException("구매자 계정에서 예매 조건을 확인할 수 있습니다.")

    response.headers["Cache-Control"] = "no-store"
    return APIResponse.ok(await reader.check(user.user_id, perf_id, perf_seat_id))


@router.get("/me/reservations")
async def my_reservations(request: Request):
    return templates.TemplateResponse(request, "my_reservations.html")


@router.get("/manage")
@router.get("/manage/catalog")
async def manage_catalog(request: Request):
    return templates.TemplateResponse(request, "manage_catalog.html")
