"""Jinja2 화면을 여는 주소를 등록한다."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(default_response_class=HTMLResponse, include_in_schema=False)
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


@router.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        request, "Home.html", {"message": "AsyncTicket에 오신 것을 환영합니다!"}
    )


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


@router.get("/manage")
async def manage(request: Request):
    return templates.TemplateResponse(request, "manage.html")


@router.get("/reservations")
async def reservations(request: Request):
    return templates.TemplateResponse(request, "reservations.html")
