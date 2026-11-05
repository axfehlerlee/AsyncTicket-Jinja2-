from asyncticket.payment.application.service import PaymentService


def provider_payment_service() -> PaymentService:
    # 실제 구현은 wiring/payment.py가 dependency_overrides로 바꿔 끼운다.
    raise NotImplementedError("PaymentService 의존성이 주입되지 않았습니다.")
