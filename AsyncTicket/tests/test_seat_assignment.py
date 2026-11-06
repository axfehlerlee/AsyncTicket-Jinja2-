import unittest
from unittest.mock import AsyncMock

from asyncticket.seats.application.service import (
    PerformanceSeatService,
    SeatReservationConflictError,
)
from asyncticket.shared.core.exceptions import ValidationException


class SeatAssignmentTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.repository = AsyncMock()
        self.service = PerformanceSeatService(self.repository, AsyncMock())
        # Test-only labels: the caller supplies the team's eventual seat states.
        self.values = dict(
            perf_id=1, perf_seat_id=2, reserv_id=3,
            expected_status="test-before", reserved_status="test-after",
        )

    async def test_success_forwards_values_without_owning_transaction(self):
        self.repository.assign_reservation.return_value = True
        self.assertIsNone(await self.service.assign_reservation(**self.values))
        self.repository.assign_reservation.assert_awaited_once_with(**self.values)
        self.repository.commit.assert_not_called()
        self.repository.flush.assert_not_called()
        self.repository.rollback.assert_not_called()

    async def test_failed_update_raises_conflict(self):
        self.repository.assign_reservation.return_value = False
        with self.assertRaises(SeatReservationConflictError) as caught:
            await self.service.assign_reservation(**self.values)
        self.assertEqual(caught.exception.error_code, "SEAT_RESERVATION_CONFLICT")
        self.repository.commit.assert_not_called()
        self.repository.rollback.assert_not_called()

    async def test_nonpositive_ids_do_not_reach_repository(self):
        for name in ("perf_id", "perf_seat_id", "reserv_id"):
            for value in (0, -1):
                with self.subTest(name=name, value=value):
                    with self.assertRaises(ValidationException) as caught:
                        await self.service.assign_reservation(
                            **{**self.values, name: value}
                        )
                    self.assertEqual(
                        caught.exception.error_code, "INVALID_SEAT_RESERVATION_ID"
                    )
        self.repository.assign_reservation.assert_not_called()

    async def test_empty_or_identical_states_do_not_reach_repository(self):
        for before, after in (("", "test-after"), ("test-before", ""), ("same", "same")):
            with self.subTest(before=before, after=after):
                with self.assertRaises(ValidationException) as caught:
                    await self.service.assign_reservation(
                        **{**self.values, "expected_status": before, "reserved_status": after}
                    )
                self.assertEqual(
                    caught.exception.error_code, "INVALID_SEAT_STATUS_TRANSITION"
                )
        self.repository.assign_reservation.assert_not_called()
