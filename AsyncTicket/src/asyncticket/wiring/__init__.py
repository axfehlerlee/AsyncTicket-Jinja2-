"""튜터의 공용 DI 조립 진입점. 기존 좌석 연결을 여기서 호출한다."""
from fastapi import FastAPI
from asyncticket.wiring.seats import wire_dependencies as wire_seat_dependencies


def wire_dependencies(app: FastAPI) -> None:
    # 각 담당자의 의존성 연결을 추가할 위치다. 이미 있는 좌석 연결은 보존한다.
    app.dependency_overrides.update({})
    wire_seat_dependencies(app)
