"""응용 계층: 결제 조회와 상태 변경 순서를 조율한다."""


from datetime import datetime
from decimal import Decimal


from asyncticket.payment.domain.payment import Payment, PaymentStatus
from asyncticket.payment.domain.repository import PaymentRepository
from asyncticket.shared.core.exceptions import ConflictException, NotFoundException


class PaymentService:
    def __init__(self, repository: PaymentRepository):
        # 저장 계약만 받는다. 세션과 테이블 클래스는 인프라 저장소 안에 있다.
        self.repository = repository

    async def get_payment(self, pay_id: int) -> Payment:
        payment = await self.repository.find_by_id(pay_id)
        if payment is None:
            raise NotFoundException(
                "결제를 찾을 수 없습니다.", error_code = "PAYMEN_NOT_FOUND"
            )
        return payment

    async def record_attempt(self, method: str, amount: Decimal) -> Payment:
        # 예매 번호가 없는 결제는 실패 상태만 규칙을 통과한다.
        payment = Payment(
            pay_id=None,
            method=method,
            amount=amount,
            status=PaymentStatus.FAILED,
        )
        await self.repository.save(payment)
        return payment
    
    async def mark_paid(
            self, pay_id: int, reserv_id:int, paid_at: datetime | None = None,
    ) -> Payment:
        # 예매 번호는 이 클래스가 만들지 않고, 호출자가 넘긴 값을 붙인다.
        payment = await self._change(pay_id, lambda item: item.mark_as_paid(reserv_id,paid_at))
        return payment

    async def mark_failed(self, pay_id: int) -> Payment:
        return await self._change(pay_id, lambda item: item.mark_as_failed())

    async def mark_refunded(
            self, pay_id: int, refunded_at: datetime | None = None,) -> Payment:
        return await self._change(pay_id, lambda item: item.mark_as_refunded(refunded_at))

    async def _change(self,pay_id: int, change) -> Payment:
        payment = await self.get_payment(pay_id)
        try:
            change(payment)
        except ValueError as exc:
            # 도메인 규칙 위반은 현재 상태와 요청이 충돌한 것으로 올린다.
            raise ConflictException(str(exc), error_code="PAYMENT_STATE_CONFLICT") from exc
        await self.repository.save(payment)
        return payment
        
