from enum import StrEnum


class PaymentStatus(StrEnum):
    FAILED = "FAIL"
    PAID = "SUCCESS"
    REFUNDED = "REFUND"
    READY = "READY"