"""공연 표현 계층의 주입 계약. 실제 객체 생성은 wiring에서 담당한다."""

from asyncticket.shows.application.service import ShowApplicationService


def provide_show_service() -> ShowApplicationService:
    raise NotImplementedError("ShowApplicationService 의존성이 주입되지 않았습니다.")
