"""도메인별 의존성 연결의 공용 진입점."""
from fastapi import FastAPI
from asyncticket.wiring.seats import wire_dependencies as wire_seat_dependencies
from asyncticket.wiring.performance_seats import wire_dependencies as wire_performance_seat_dependencies


def wire_dependencies(app: FastAPI) -> None:
    wire_seat_dependencies(app)
    wire_performance_seat_dependencies(app)
