from asyncticket.seats.application.service import SeatService


def provide_seat_service() -> SeatService:
    """튜터 예제처럼 container.py에서 실제 서비스 생성 함수로 연결한다."""
    raise NotImplementedError("좌석 서비스 의존성이 연결되지 않았습니다.")
