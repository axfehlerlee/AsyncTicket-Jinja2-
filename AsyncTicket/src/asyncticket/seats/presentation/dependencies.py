from asyncticket.seats.application.service import SeatInfoService


def provide_seat_info_service() -> SeatInfoService:
    raise NotImplementedError("좌석 등급 서비스 의존성이 연결되지 않았습니다.")
