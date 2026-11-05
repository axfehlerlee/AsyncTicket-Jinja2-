"""도메인별 의존성 연결의 공용 진입점."""
from fastapi import FastAPI
from asyncticket.wiring.shows import wire_dependencies as wire_show_dependencies
from asyncticket.wiring.performances import wire_dependencies as wire_performance_dependencies
from asyncticket.wiring.venues import wire_dependencies as wire_venue_dependencies


def wire_dependencies(app: FastAPI) -> None:
    wire_show_dependencies(app)
    wire_performance_dependencies(app)
    wire_venue_dependencies(app)
