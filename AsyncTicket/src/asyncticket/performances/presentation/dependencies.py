"""회차 표현 계층의 주입 계약. 실제 객체 생성은 wiring에서 담당한다."""

from asyncticket.performances.application.service import PerformanceApplicationService


def provide_performance_service() -> PerformanceApplicationService:
    raise NotImplementedError("PerformanceApplicationService 의존성이 주입되지 않았습니다.")
