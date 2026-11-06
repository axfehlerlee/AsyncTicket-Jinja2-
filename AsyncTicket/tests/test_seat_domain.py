"""DB 없이 좌석 도메인의 정상·경계·실패 조건을 확인한다."""

from dataclasses import FrozenInstanceError
import unittest

from asyncticket.seats.domain.seat_info import SeatInfo
from asyncticket.seats.domain.enums import SeatGrade


class SeatInfoTests(unittest.TestCase):
    def setUp(self):
        self.grade = SeatInfo(
            seat_id=101, perf_id=10, name=SeatGrade.R, total_seat=30, price=55000
        )

    def test_remaining_seats(self):
        self.assertEqual(self.grade.remaining_seats(8), 22)

    def test_exact_remaining_quantity_is_allowed(self):
        self.assertIsNone(self.grade.require_capacity(22, 8))

    def test_insufficient_capacity_is_rejected_without_mutation(self):
        with self.assertRaisesRegex(ValueError, "남은 좌석"):
            self.grade.require_capacity(23, 8)
        self.assertEqual(self.grade.remaining_seats(8), 22)

    def test_invalid_quantities(self):
        for quantity in (0, -1, True, "1"):
            with self.subTest(quantity=quantity):
                with self.assertRaises(ValueError):
                    self.grade.require_capacity(quantity, 0)

    def test_invalid_occupied_counts(self):
        for count in (-1, 31, True, "8"):
            with self.subTest(count=count):
                with self.assertRaises(ValueError):
                    self.grade.remaining_seats(count)

    def test_invalid_identifiers(self):
        for field in ("seat_id", "perf_id"):
            for value in (0, -1, True, "10"):
                with self.subTest(field=field, value=value):
                    values = dict(seat_id=101, perf_id=10, name=SeatGrade.R, total_seat=30, price=55000)
                    values[field] = value
                    with self.assertRaises(ValueError):
                        SeatInfo(**values)

    def test_invalid_capacity_or_price(self):
        for field in ("total_seat", "price"):
            for value in (-1, True, "100"):
                with self.subTest(field=field, value=value):
                    values = dict(seat_id=101, perf_id=10, name=SeatGrade.R, total_seat=30, price=55000)
                    values[field] = value
                    with self.assertRaises(ValueError):
                        SeatInfo(**values)

    def test_incomplete_configuration_is_rejected_at_creation(self):
        with self.assertRaises(TypeError):
            SeatInfo(seat_id=101, perf_id=10)

    def test_each_required_configuration_field(self):
        for field, value in (("name", None), ("name", " "), ("total_seat", None), ("price", None)):
            with self.subTest(field=field, value=value):
                values = dict(seat_id=101, perf_id=10, name=SeatGrade.R, total_seat=30, price=55000)
                values[field] = value
                with self.assertRaises(ValueError):
                    SeatInfo(**values)

    def test_nonnegative_price_and_positive_capacity_boundaries(self):
        for field, value in (("total_seat", 0), ("price", -1)):
            with self.subTest(field=field, value=value):
                values = dict(seat_id=101, perf_id=10, name=SeatGrade.R, total_seat=30, price=0)
                values[field] = value
                with self.assertRaises(ValueError):
                    SeatInfo(**values)
        minimum = SeatInfo(seat_id=101, perf_id=10, name=SeatGrade.R, total_seat=1, price=0)
        for price in (0, 1, 49999):
            with self.subTest(price=price):
                grade = SeatInfo(seat_id=101, perf_id=10, name=SeatGrade.R, total_seat=1, price=price)
                self.assertEqual(grade.price, price)
        self.assertEqual(minimum.remaining_seats(0), 1)
        self.assertEqual(minimum.remaining_seats(1), 0)
        with self.assertRaises(ValueError):
            minimum.require_capacity(1, 1)

    def test_invalid_grade_name(self):
        for name in (False, 42, "가" * 256):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    SeatInfo(seat_id=101, perf_id=10, name=name, total_seat=30, price=55000)

    def test_validated_values_cannot_be_changed_directly(self):
        with self.assertRaises(FrozenInstanceError):
            self.grade.total_seat = -1


if __name__ == "__main__":
    unittest.main()
