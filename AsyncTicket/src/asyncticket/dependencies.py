"""기존 서비스 override import의 호환 경로. 객체 생성은 wiring/catalog.py로 이동했다."""

from asyncticket.performances.presentation.dependencies import (
    provide_performance_service as get_performance_service,
)
from asyncticket.shows.presentation.dependencies import provide_show_service as get_show_service

__all__ = ["get_show_service", "get_performance_service"]
