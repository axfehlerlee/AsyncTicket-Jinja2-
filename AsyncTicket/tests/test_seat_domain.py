"""좌석 도메인·서비스·저장소·ASGI 검증. 실제 PG·운영 인증 검사는 아니다."""

import ast
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import unittest
from asyncticket.seats.domain.performanc_seat import PerformanceSeat
from asyncticket.seats.domain.seat_info import SeatInfo
import asyncio
from dataclasses import replace
from unittest.mock import create_autospec
from asyncticket.seats.application.service import SeatInfoService
from asyncticket.seats.domain.repository import PerformanceSeatRepository, SeatInfoRepository
from asyncticket.shared.core.exceptions import ConflictException, NotFoundException, SharedException
from asyncticket.shared.domain.catalog import CatalogPolicy
from unittest.mock import patch
from sqlalchemy import BigInteger, Column, Integer, MetaData, Table, create_engine, event, func, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session
from asyncticket.seats.infrastructure.models import PerformanceSeats, SeatsInfoModel
from asyncticket.shared.core.models import Base, init_models
from asyncticket.wiring.seats import create_seat_info_service
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from fastapi import FastAPI
from sqlalchemy import BigInteger, Column, DateTime, Integer, MetaData, Numeric, Table, create_engine, event, func, select
from asyncticket.seats.presentation.router import router as seat_router
from asyncticket.wiring.seats import wire_dependencies as wire_seat_dependencies
from asyncticket.wiring.performance_seats import wire_dependencies as wire_performance_seat_dependencies
from asyncticket.shared.core.exception_handlers import register_exception_handlers
from asyncticket.shared.core.models import init_models
from asyncticket.shared.domain.catalog import CatalogActor, CatalogPolicy
from asyncticket.shared.presentation.catalog_http import register_catalog_errors
from test_catalog import asgi_request


class SeatInfoTests(unittest.TestCase):
    def setUp(self):
        self.grade = SeatInfo(seat_id=101, perf_id=10, name="R석", total_seat=2, price=50000)

    def test_factory_has_no_id(self):
        grade = SeatInfo.create(perf_id=10, name="R석", total_seat=2, price=50000)
        self.assertIsNone(grade.seat_id)

    def test_keyword_only_constructor(self):
        with self.assertRaises(TypeError):
            SeatInfo(10, "R석", 2, 50000)

    def test_remaining_and_exact_capacity(self):
        self.assertEqual(self.grade.remaining_seats(1), 1)
        self.assertIsNone(self.grade.require_capacity(1, 1))
        self.assertEqual(self.grade.remaining_seats(2), 0)

    def test_invalid_quantities(self):
        for quantity in (0, -1, True, "1", 1.5, 3):
            with self.subTest(quantity=quantity), self.assertRaises(ValueError):
                self.grade.require_capacity(quantity, 0)

    def test_invalid_occupied_counts(self):
        for count in (-1, 3, True, "1", None):
            with self.subTest(count=count), self.assertRaises(ValueError):
                self.grade.remaining_seats(count)

    def test_invalid_identifiers(self):
        for field in ("seat_id", "perf_id"):
            for value in (0, -1, True, "10", 1.5):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    replace(self.grade, **{field: value})

    def test_capacity_and_current_price_boundary(self):
        for field, invalid in (("total_seat", (0, -1, True, "2", None)),
                               ("price", (0, 49999, -1, True, "50000", None))):
            for value in invalid:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    replace(self.grade, **{field: value})

    def test_grade_name_boundaries(self):
        for value in (None, False, 42, "", " ", "가" * 256):
            with self.subTest(value=value), self.assertRaises(ValueError):
                replace(self.grade, name=value)
        self.assertEqual(len(replace(self.grade, name="가" * 255).name), 255)

    def test_validated_fields_are_frozen(self):
        with self.assertRaises(FrozenInstanceError):
            self.grade.total_seat = -1

    def test_create_seats_uses_grade_id(self):
        seats = self.grade.create_seats(["A01", "A02"])
        self.assertEqual([seat.seat_id for seat in seats], [101, 101])
        self.assertEqual([seat.seat_seq for seat in seats], ["A01", "A02"])
        self.assertTrue(all(seat.perf_seat_id is None and seat.reserv_id is None for seat in seats))
        self.assertTrue(all(seat.status == "AVAILABLE" for seat in seats))

    def test_unsaved_grade_cannot_create_seats(self):
        with self.assertRaises(ValueError):
            replace(self.grade, seat_id=None).create_seats(["A01", "A02"])

    def test_invalid_names_rejected_before_id_assignment(self):
        grade = replace(self.grade, seat_id=None)
        for names in ([], ["A01"], ["A01", "A01"], ["A01", " "], ["A01", None],
                      ["A01", "가" * 256]):
            with self.subTest(names=names), self.assertRaises(ValueError):
                grade.validate_seat_names(names)

    def test_domain_has_no_framework_imports(self):
        folder = Path(__file__).parents[1] / "src/asyncticket/seats/domain"
        for path in folder.glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                modules = ([node.module or ""] if isinstance(node, ast.ImportFrom) else
                           [alias.name for alias in node.names] if isinstance(node, ast.Import) else [])
                for module in modules:
                    self.assertTrue(module in ("abc", "dataclasses", "datetime", "decimal") or
                                    module.startswith("asyncticket.seats.domain"), (path.name, module))


class PerformanceSeatTests(unittest.TestCase):
    def setUp(self):
        self.seat = PerformanceSeat(seat_id=101, seat_seq="A01", status="AVAILABLE")

    def test_unbooked_and_existing_identity(self):
        self.assertIsNone(self.seat.reserv_id)
        existing = replace(self.seat, perf_seat_id=1, reserv_id=2)
        self.assertEqual((existing.perf_seat_id, existing.reserv_id), (1, 2))

    def test_invalid_ids(self):
        for field in ("seat_id", "perf_seat_id", "reserv_id"):
            for value in (0, -1, True, "1", 1.5):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    replace(self.seat, **{field: value})

    def test_names_and_status_boundaries(self):
        for field, limit in (("seat_seq", 255), ("status", 30)):
            for value in (None, False, 12, "", " ", "a" * (limit + 1)):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    replace(self.seat, **{field: value})
            self.assertEqual(len(getattr(replace(self.seat, **{field: "a" * limit}), field)), limit)

    def test_status_vocabulary_is_not_invented(self):
        self.assertEqual(replace(self.seat, status="CUSTOM_STATUS").status, "CUSTOM_STATUS")


class SeatApplicationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.grades = create_autospec(SeatInfoRepository, instance=True)
        self.seats = create_autospec(PerformanceSeatRepository, instance=True)
        self.service = SeatInfoService(self.grades, self.seats, CatalogPolicy())
        self.grade = SeatInfo.create(perf_id=10, name="R석", total_seat=2, price=50000)
        self.grades.lock_performance.return_value = True
        self.grades.grade_exists.return_value = False
        self.seats.names_exist.return_value = False
        self.grades.save_seat_info.return_value = replace(self.grade, seat_id=101)

    async def test_invalid_management_context_rolls_back_without_writes(self):
        future = datetime.now(timezone.utc) + timedelta(days=1)
        cases = [
            ({"owner_id": value, "booking_opens_at": future}, "INVALID_SHOW_OWNER")
            for value in (None, True, "1", 0, -1)
        ] + [
            ({"owner_id": 1, "booking_opens_at": value}, "INVALID_BOOKING_TIME")
            for value in (None, "2026-11-06", 1, future.replace(tzinfo=None))
        ]
        for context, code in cases:
            with self.subTest(context=context):
                self.grades.reset_mock()
                self.seats.reset_mock()
                self.grades.get_management_context.return_value = context
                with self.assertRaises(SharedException) as raised:
                    await self.service.create(self.grade, ["A01", "A02"], CatalogActor(1, "SELLER"))
                self.assertEqual((raised.exception.status_code, raised.exception.error_code), (503, code))
                self.grades.save_seat_info.assert_not_awaited()
                self.seats.save_many.assert_not_awaited()
                self.grades.commit.assert_not_awaited()
                self.grades.rollback.assert_awaited_once()

    async def test_sale_start_exact_boundary(self):
        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 11, 6, tzinfo=timezone.utc)

        now = FixedDateTime.now(timezone.utc)
        with patch("asyncticket.seats.application.service.datetime", FixedDateTime):
            for delta in (1, 0, -1):
                with self.subTest(seconds_until_sale=delta):
                    self.grades.reset_mock()
                    self.seats.reset_mock()
                    self.grades.get_management_context.return_value = {
                        "owner_id": 1, "booking_opens_at": now + timedelta(seconds=delta),
                    }
                    if delta > 0:
                        await self.service.create(self.grade, ["A01", "A02"], CatalogActor(1, "SELLER"))
                        self.grades.commit.assert_awaited_once()
                    else:
                        with self.assertRaises(ConflictException) as raised:
                            await self.service.create(self.grade, ["A01", "A02"], CatalogActor(1, "SELLER"))
                        self.assertEqual(raised.exception.error_code, "SEAT_SALE_STARTED")
                        self.grades.save_seat_info.assert_not_awaited()
                        self.seats.save_many.assert_not_awaited()
                        self.grades.rollback.assert_awaited_once()

    async def test_configuration_order_and_shared_commit(self):
        events = []
        async def lock(perf_id):
            events.append("lock")
            return True
        async def grade_exists(perf_id, name):
            events.append("grade_exists")
            return False
        async def names_exist(perf_id, names):
            events.append("names_exist")
            return False
        async def save(grade):
            events.append("save_grade")
            return replace(grade, seat_id=101)
        async def save_many(seats):
            events.append("save_seats")
            self.assertEqual([seat.seat_id for seat in seats], [101, 101])
        async def commit():
            events.append("commit")
        self.grades.lock_performance.side_effect = lock
        self.grades.grade_exists.side_effect = grade_exists
        self.seats.names_exist.side_effect = names_exist
        self.grades.save_seat_info.side_effect = save
        self.seats.save_many.side_effect = save_many
        self.grades.commit.side_effect = commit
        saved = await self.service.create_seat_configuration(self.grade, ["A01", "A02"])
        self.assertEqual(saved.seat_id, 101)
        self.assertEqual(events, ["lock", "grade_exists", "names_exist", "save_grade", "save_seats", "commit"])
        self.grades.rollback.assert_not_awaited()

    async def test_bad_names_do_not_reach_database(self):
        for names in (["A01"], ["A01", "A01"], ["A01", " "], ["A01", None]):
            with self.subTest(names=names), self.assertRaises(ValueError):
                await self.service.create_seat_configuration(self.grade, names)
        self.grades.lock_performance.assert_not_awaited()
        self.grades.save_seat_info.assert_not_awaited()
        self.seats.save_many.assert_not_awaited()
        self.grades.commit.assert_not_awaited()

    async def test_existing_id_is_not_a_new_configuration(self):
        with self.assertRaises(ValueError):
            await self.service.create_seat_configuration(replace(self.grade, seat_id=101), ["A01", "A02"])
        self.grades.lock_performance.assert_not_awaited()

    async def test_missing_performance(self):
        self.grades.lock_performance.return_value = False
        with self.assertRaises(NotFoundException):
            await self.service.create_seat_configuration(self.grade, ["A01", "A02"])
        self.grades.save_seat_info.assert_not_awaited()
        self.grades.rollback.assert_awaited_once()

    async def test_duplicate_grade_and_names(self):
        self.grades.grade_exists.return_value = True
        with self.assertRaises(ConflictException):
            await self.service.create_seat_configuration(self.grade, ["A01", "A02"])
        self.seats.names_exist.assert_not_awaited()
        self.grades.grade_exists.return_value = False
        self.seats.names_exist.return_value = True
        with self.assertRaises(ConflictException):
            await self.service.create_seat_configuration(self.grade, ["A01", "A02"])
        self.grades.save_seat_info.assert_not_awaited()
        self.grades.commit.assert_not_awaited()

    async def test_write_commit_and_cancellation_failures_rollback(self):
        for method, error in (("save_many", RuntimeError("seat save failed")),
                              ("commit", RuntimeError("commit failed")),
                              ("save_many", asyncio.CancelledError())):
            with self.subTest(error=type(error).__name__):
                self.setUp()
                target = getattr(self.grades if method == "commit" else self.seats, method)
                target.side_effect = error
                with self.assertRaises(type(error)):
                    await self.service.create_seat_configuration(self.grade, ["A01", "A02"])
                self.grades.rollback.assert_awaited_once()

    async def test_missing_grade_and_capacity_alias(self):
        self.grades.get_seat_info.return_value = None
        with self.assertRaises(NotFoundException):
            await self.service.get_seat_info(999)
        self.grades.get_seat_info.return_value = replace(self.grade, seat_id=101)
        await self.service.check_capacity(101, 1, 1)
        with self.assertRaises(ValueError):
            await self.service.check_seat_availability(101, 2, 1)

    async def test_price_save_commits_and_rolls_back_failure(self):
        saved = replace(self.grade, seat_id=101)
        self.grades.get_seat_info.return_value = saved
        await self.service.save_seat_info(replace(saved, price=60000))
        self.grades.commit.assert_awaited_once()
        self.grades.lock_performance.assert_awaited_once_with(10)
        self.grades.save_seat_info.side_effect = RuntimeError("save failed")
        with self.assertRaises(RuntimeError):
            await self.service.save_seat_info(saved)
        self.grades.rollback.assert_awaited_once()

    async def test_standalone_grade_creation_is_rejected(self):
        with self.assertRaises(ValueError):
            await self.service.save_seat_info(self.grade)
        self.grades.save_seat_info.assert_not_awaited()
        self.grades.commit.assert_not_awaited()

    async def test_saved_configuration_changes_are_rejected(self):
        saved = replace(self.grade, seat_id=101)
        self.grades.get_seat_info.return_value = saved
        for changes in ({"perf_id": 20}, {"name": "S석"}, {"total_seat": 1}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                await self.service.save_seat_info(replace(saved, **changes))
        self.grades.save_seat_info.assert_not_awaited()
        self.grades.commit.assert_not_awaited()


class SessionAdapter:
    """동기 SQLite 세션을 비동기 저장소의 테스트 경계에 연결한다."""

    def __init__(self, session):
        self.session = session
        self.statements = []

    async def scalar(self, stmt):
        self.statements.append(stmt)
        return self.session.scalar(stmt)

    def add(self, model):
        self.session.add(model)

    def add_all(self, models):
        self.session.add_all(models)

    async def flush(self):
        self.session.flush()

    async def refresh(self, model):
        self.session.refresh(model)

    async def commit(self):
        self.session.commit()

    async def rollback(self):
        self.session.rollback()


class SeatInfrastructureTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        init_models()
        self.engine = create_engine("sqlite:///:memory:")
        @event.listens_for(self.engine, "connect")
        def enable_fk(connection, record):
            connection.execute("PRAGMA foreign_keys=ON")
        metadata = MetaData()
        self.performances = Table("performances", metadata, Column("perf_id", BigInteger, primary_key=True))
        Table("reservations", metadata, Column("reserv_id", BigInteger, primary_key=True))
        SeatsInfoModel.__table__.to_metadata(metadata)
        PerformanceSeats.__table__.to_metadata(metadata)
        metadata.create_all(self.engine)
        with self.engine.begin() as connection:
            connection.execute(self.performances.insert(), [{"perf_id": 10}, {"perf_id": 20}])
        self.session = Session(self.engine, expire_on_commit=False)
        self.adapter = SessionAdapter(self.session)
        self.service = create_seat_info_service(self.adapter)
        self.grade = SeatInfo.create(perf_id=10, name="R석", total_seat=2, price=50000)

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def counts(self):
        with Session(self.engine) as observer:
            return (observer.scalar(select(func.count()).select_from(SeatsInfoModel)),
                    observer.scalar(select(func.count()).select_from(PerformanceSeats)))

    def test_incomplete_grade_conversion_preserves_domain_errors(self):
        fields = {"seat_id": 1, "perf_id": 10, "name": "R석", "total_seat": 2, "price": 50000}
        for field in ("name", "total_seat", "price"):
            with self.subTest(field=field):
                values = {**fields, field: None}
                with self.assertRaises(ValueError) as expected:
                    SeatInfo(**values)
                with self.assertRaises(ValueError) as actual:
                    SeatsInfoModel(**values).to_seat_info()
                self.assertEqual(str(actual.exception), str(expected.exception))

    def test_incomplete_seat_conversion_preserves_domain_error(self):
        with self.assertRaises(ValueError) as expected:
            PerformanceSeat(seat_id=1, seat_seq=None, status="AVAILABLE")
        with self.assertRaises(ValueError) as actual:
            PerformanceSeats(seat_id2=1, seat_seq=None, status="AVAILABLE").to_performance_seat()
        self.assertEqual(str(actual.exception), str(expected.exception))

    async def test_create_persists_both_tables_and_round_trips(self):
        saved = await self.service.create_seat_configuration(self.grade, ["A01", "A02"])
        self.assertIsNotNone(saved.seat_id)
        self.assertIsNone(self.grade.seat_id)
        self.assertEqual(self.counts(), (1, 2))
        self.assertEqual(await self.service.get_seat_info(saved.seat_id), saved)
        seats = self.session.scalars(select(PerformanceSeats).order_by(PerformanceSeats.perf_seat_id)).all()
        self.assertEqual([row.to_performance_seat().seat_seq for row in seats], ["A01", "A02"])
        self.assertTrue(all(row.seat_id2 == saved.seat_id and row.reserv_id is None for row in seats))

    async def test_wiring_shares_one_session(self):
        self.assertIs(self.service.repository.session, self.adapter)
        self.assertIs(self.service.performance_seat_repository.session, self.adapter)
        self.assertIs(SeatsInfoModel.metadata, Base.metadata)

    async def test_repositories_flush_without_commit(self):
        saved = await self.service.repository.save_seat_info(self.grade)
        await self.service.performance_seat_repository.save_many(saved.create_seats(["A01", "A02"]))
        await self.service.repository.rollback()
        self.assertEqual(self.counts(), (0, 0))

    async def test_failure_after_seat_insert_rolls_back_both_tables(self):
        original = self.service.performance_seat_repository.save_many
        async def failing_save(seats):
            await original(seats)
            raise RuntimeError("failure after seat flush")
        with patch.object(self.service.performance_seat_repository, "save_many", failing_save):
            with self.assertRaises(RuntimeError):
                await self.service.create_seat_configuration(self.grade, ["A01", "A02"])
        self.assertEqual(self.counts(), (0, 0))

    async def test_invalid_names_write_nothing(self):
        with self.assertRaises(ValueError):
            await self.service.create_seat_configuration(self.grade, ["A01", " "])
        self.assertEqual(self.adapter.statements, [])
        self.assertEqual(self.counts(), (0, 0))

    async def test_missing_performance_and_grade(self):
        with self.assertRaises(NotFoundException):
            await self.service.create_seat_configuration(replace(self.grade, perf_id=99), ["A01", "A02"])
        with self.assertRaises(NotFoundException):
            await self.service.get_seat_info(999)
        self.assertEqual(self.counts(), (0, 0))

    async def test_duplicates_scoped_to_performance(self):
        await self.service.create_seat_configuration(self.grade, ["A01", "A02"])
        with self.assertRaises(ConflictException):
            await self.service.create_seat_configuration(self.grade, ["B01", "B02"])
        with self.assertRaises(ConflictException):
            await self.service.create_seat_configuration(replace(self.grade, name="S석"), ["A01", "B02"])
        await self.service.create_seat_configuration(replace(self.grade, perf_id=20), ["A01", "A02"])
        self.assertEqual(self.counts(), (2, 4))

    async def test_lock_sql_is_postgresql_for_update(self):
        self.assertTrue(await self.service.repository.lock_performance(10))
        stmt = self.adapter.statements[-1]
        sql = str(stmt.compile(dialect=postgresql.dialect()))
        self.assertIn("FOR UPDATE", sql)
        self.assertIn("WHERE performances.perf_id", sql)
        self.assertFalse(await self.service.repository.lock_performance(999))

    async def test_existing_grade_update_and_missing_update(self):
        saved = await self.service.create_seat_configuration(self.grade, ["A01", "A02"])
        changed = await self.service.save_seat_info(replace(saved, price=60000))
        self.assertEqual(changed.price, 60000)
        with self.assertRaises(NotFoundException):
            await self.service.save_seat_info(replace(saved, seat_id=999))
        with self.assertRaises(ValueError):
            await self.service.save_seat_info(replace(saved, perf_id=20))
        self.assertEqual((await self.service.get_seat_info(saved.seat_id)).perf_id, 10)

    async def test_fk_failure_rolls_back_individual_seat_list(self):
        seats = replace(self.grade, seat_id=999).create_seats(["A01", "A02"])
        from sqlalchemy.exc import IntegrityError
        with self.assertRaises(IntegrityError):
            try:
                await self.service.performance_seat_repository.save_many(seats)
                await self.service.repository.commit()
            except Exception:
                await self.service.repository.rollback()
                raise
        self.assertEqual(self.counts(), (0, 0))

    async def test_incomplete_legacy_row_is_not_a_valid_configuration(self):
        model = SeatsInfoModel(perf_id=10)
        self.session.add(model)
        self.session.commit()
        with self.assertRaises(ValueError):
            await self.service.get_seat_info(model.seat_id)

    async def test_names_exist_handles_empty_list(self):
        self.assertFalse(await self.service.performance_seat_repository.names_exist(10, []))

    def test_postgresql_schema_preserves_column_types(self):
        self.assertIsInstance(SeatsInfoModel.__table__.c.seat_id.type.dialect_impl(postgresql.dialect()), BigInteger)
        self.assertEqual(PerformanceSeats.__table__.c.seat_id2.foreign_keys.copy().pop().target_fullname, "seats_info.seat_id")

    async def test_public_grade_save_cannot_duplicate_or_resize_configuration(self):
        saved = await self.service.create_seat_configuration(self.grade, ["A01", "A02"])
        for grade in (self.grade, replace(saved, total_seat=1), replace(saved, name="S석")):
            with self.subTest(grade=grade), self.assertRaises(ValueError):
                await self.service.save_seat_info(grade)
        self.assertEqual(self.counts(), (1, 2))
        self.assertEqual((await self.service.get_seat_info(saved.seat_id)).total_seat, 2)


class QuerySessionAdapter(SessionAdapter):
    async def execute(self, stmt):
        self.statements.append(stmt)
        result = self.session.execute(stmt)
        rows = []
        for row in result.mappings():
            rows.append({key: value.replace(tzinfo=timezone.utc)
                         if isinstance(value, datetime) and value.utcoffset() is None else value
                         for key, value in row.items()})
        class Mappings:
            def mappings(self):
                return self
            def __iter__(self):
                return iter(rows)
            def all(self):
                return rows
            def one_or_none(self):
                if len(rows) > 1:
                    raise AssertionError("fixture query expected at most one row")
                return rows[0] if rows else None
        return Mappings()


class Authenticator:
    async def authenticate(self, token):
        return {"owner": CatalogActor(1, "SELLER"), "other": CatalogActor(2, "SELLER"),
                "admin": CatalogActor(3, "ADMIN"), "buyer": CatalogActor(4, "BUYER")}.get(token)


class SeatApiTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        init_models()
        self.engine = create_engine("sqlite:///:memory:")
        @event.listens_for(self.engine, "connect")
        def enable_fk(connection, record):
            connection.execute("PRAGMA foreign_keys=ON")
        self.metadata = MetaData()
        self.shows = Table("shows", self.metadata, Column("show_id", BigInteger, primary_key=True),
                           Column("user_id", BigInteger, nullable=False))
        self.performances = Table("performances", self.metadata,
            Column("perf_id", BigInteger, primary_key=True), Column("show_id", BigInteger, nullable=False),
            Column("booking_opens_at", DateTime(timezone=True), nullable=False))
        self.reservations = Table("reservations", self.metadata,
            Column("reserv_id", BigInteger, primary_key=True), Column("user_id", BigInteger, nullable=False),
            Column("perf_id", BigInteger, nullable=False), Column("quantity", Integer, nullable=False),
            Column("total_amount", Numeric(12, 2), nullable=False))
        SeatsInfoModel.__table__.to_metadata(self.metadata)
        PerformanceSeats.__table__.to_metadata(self.metadata)
        self.metadata.create_all(self.engine)
        future = datetime.now(timezone.utc) + timedelta(days=30)
        with self.engine.begin() as connection:
            connection.execute(self.shows.insert(), [{"show_id": 1, "user_id": 1}, {"show_id": 2, "user_id": 2}])
            connection.execute(self.performances.insert(), [
                {"perf_id": 10, "show_id": 1, "booking_opens_at": future},
                {"perf_id": 20, "show_id": 2, "booking_opens_at": future},
                {"perf_id": 30, "show_id": 1, "booking_opens_at": future}])
            connection.execute(self.reservations.insert(), [
                {"reserv_id": 100, "user_id": 1, "perf_id": 10, "quantity": 2, "total_amount": Decimal("110000.00")},
                {"reserv_id": 200, "user_id": 2, "perf_id": 20, "quantity": 1, "total_amount": Decimal("50000.00")}])
        self.session = Session(self.engine, expire_on_commit=False)
        self.adapter = QuerySessionAdapter(self.session)
        async def test_db():
            try:
                yield self.adapter
            finally:
                self.session.rollback()
        self.test_db = test_db
        self.app = FastAPI()
        self.app.state.catalog_authenticator = Authenticator()
        self.app.state.catalog_policy = CatalogPolicy()
        register_exception_handlers(self.app)
        register_catalog_errors(self.app)
        wire_seat_dependencies(self.app, test_db)
        wire_performance_seat_dependencies(self.app, test_db)
        self.app.include_router(seat_router)
        self.body = {"name": "R석", "total_seat": 2, "price": 55000, "seat_seqs": ["A01", "A02"]}

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    async def request(self, method, path, body=None, token=None):
        return await asgi_request(self.app, method, path, body, token, raise_server_exceptions=False)

    async def create_grade(self, perf_id=10, body=None, token="owner"):
        return await self.request("POST", f"/v1/performances/{perf_id}/seat-infos", body or self.body, token)

    def counts(self):
        return (self.session.scalar(select(func.count()).select_from(SeatsInfoModel)),
                self.session.scalar(select(func.count()).select_from(PerformanceSeats)))

    async def test_create_atomic_configuration_and_follow_location(self):
        status, headers, data = await self.create_grade()
        self.assertEqual(status, 201, data)
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["total_seat"], 2)
        self.assertEqual(self.counts(), (1, 2))
        status, _, read = await self.request("GET", headers[b"location"].decode())
        self.assertEqual(status, 200)
        self.assertEqual(read["data"], data["data"])

    async def test_list_and_detail_preserve_status_and_hide_reservation(self):
        await self.create_grade()
        status, _, payload = await self.request("GET", "/v1/performances/10/seats")
        self.assertEqual(status, 200)
        self.assertEqual([item["seat_seq"] for item in payload["data"]["items"]], ["A01", "A02"])
        for item in payload["data"]["items"]:
            self.assertNotIn("reserv_id", item)
            self.assertNotIn("user_id", item)
            self.assertNotIn("available", item)
            self.assertEqual(item["status"], "AVAILABLE")
        status, _, detail = await self.request("GET", "/v1/performances/10/seats/A01")
        self.assertEqual(status, 200)
        self.assertEqual(detail["data"], payload["data"]["items"][0])
        self.assertEqual(self.counts(), (1, 2))

    async def test_existing_empty_performance_is_200(self):
        status, _, data = await self.request("GET", "/v1/performances/30/seats")
        self.assertEqual((status, data["data"]["items"]), (200, []))

    async def test_missing_performance_or_seat_is_404(self):
        for path in ("/v1/performances/999/seats", "/v1/performances/10/seats/MISSING",
                     "/v1/performances/10/seat-infos/999"):
            with self.subTest(path=path):
                status, _, data = await self.request("GET", path)
                self.assertEqual(status, 404, data)
                self.assertFalse(data["success"])

    async def test_same_seat_name_in_different_performances(self):
        await self.create_grade()
        await self.create_grade(perf_id=20, token="other")
        first = (await self.request("GET", "/v1/performances/10/seats/A01"))[2]["data"]
        second = (await self.request("GET", "/v1/performances/20/seats/A01"))[2]["data"]
        self.assertEqual((first["perf_id"], second["perf_id"]), (10, 20))
        self.assertNotEqual(first["perf_seat_id"], second["perf_seat_id"])

    async def test_grade_cannot_be_read_from_wrong_performance(self):
        _, _, created = await self.create_grade()
        seat_id = created["data"]["seat_id"]
        status, _, _ = await self.request("GET", f"/v1/performances/20/seat-infos/{seat_id}")
        self.assertEqual(status, 404)

    async def test_duplicate_grade_and_seat_names_return_409(self):
        await self.create_grade()
        for body in (self.body, {**self.body, "name": "S석"}):
            status, _, data = await self.create_grade(body=body)
            self.assertEqual(status, 409, data)
        self.assertEqual(self.counts(), (1, 2))

    async def test_invalid_request_never_writes(self):
        cases = ({"total_seat": True}, {"total_seat": 0}, {"price": 49999}, {"price": True},
                 {"price": 2147483648}, {"name": " "}, {"seat_seqs": ["A01"]},
                 {"seat_seqs": ["A01", "A01"]}, {"seat_seqs": ["A01", " "]},
                 {"seat_seqs": ["A01", None]}, {"user_id": 1}, {"seat_id": 1})
        for changes in cases:
            with self.subTest(changes=changes):
                status, _, data = await self.create_grade(body={**self.body, **changes})
                self.assertEqual(status, 422, data)
        self.assertEqual(self.counts(), (0, 0))

    async def test_invalid_path_ids_are_422(self):
        for value in ("0", "-1", "not-an-id", "9223372036854775808"):
            status, _, data = await self.request("GET", f"/v1/performances/{value}/seats")
            self.assertEqual(status, 422, data)

    async def test_create_authentication_and_permissions(self):
        for token, expected in ((None, 401), ("invalid", 401), ("buyer", 403), ("other", 403)):
            with self.subTest(token=token):
                status, headers, data = await self.create_grade(token=token)
                self.assertEqual(status, expected, data)
                if expected == 401:
                    self.assertEqual(headers[b"www-authenticate"], b"Bearer")
        self.assertEqual(self.counts(), (0, 0))

    async def test_admin_can_create(self):
        self.assertEqual((await self.create_grade(token="admin"))[0], 201)

    async def test_auth_adapter_missing_is_503(self):
        self.app.state.catalog_authenticator = None
        status, _, data = await self.create_grade()
        self.assertEqual(status, 503, data)
        self.assertEqual(self.counts(), (0, 0))

    async def test_sales_started_blocks_create_and_price_changes(self):
        _, _, created = await self.create_grade()
        self.session.execute(self.performances.update().where(self.performances.c.perf_id == 10).values(
            booking_opens_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
        self.session.commit()
        self.assertEqual((await self.create_grade(body={**self.body, "name": "S석", "seat_seqs": ["B01", "B02"]}))[0], 409)
        seat_id = created["data"]["seat_id"]
        status, _, _ = await self.request("PATCH", f"/v1/performances/10/seat-infos/{seat_id}", {"price": 60000}, "owner")
        self.assertEqual(status, 409)

    async def test_price_change_and_only_price_is_patchable(self):
        _, _, created = await self.create_grade()
        seat_id = created["data"]["seat_id"]
        path = f"/v1/performances/10/seat-infos/{seat_id}"
        status, _, data = await self.request("PATCH", path, {"price": 60000}, "owner")
        self.assertEqual((status, data["data"]["price"]), (200, 60000))
        for body in ({}, {"price": None}, {"price": 60000, "total_seat": 1}, {"name": "S석"}):
            self.assertEqual((await self.request("PATCH", path, body, "owner"))[0], 422)
        self.assertEqual((await self.request("PATCH", path, {"price": 60000}, "other"))[0], 403)
        self.assertEqual(self.counts(), (1, 2))

    async def test_patch_grade_from_other_performance_fails(self):
        _, _, created = await self.create_grade()
        path = f"/v1/performances/20/seat-infos/{created['data']['seat_id']}"
        self.assertEqual((await self.request("PATCH", path, {"price": 60000}, "other"))[0], 404)

    async def test_failure_after_seat_flush_rolls_back(self):
        from asyncticket.seats.infrastructure.repositories import SqlAlchemyPerformanceSeatRepository
        original = SqlAlchemyPerformanceSeatRepository.save_many
        async def fail(repository, seats):
            await original(repository, seats)
            raise RuntimeError("synthetic seat failure")
        with patch.object(SqlAlchemyPerformanceSeatRepository, "save_many", fail):
            status, _, data = await self.create_grade()
        self.assertEqual(status, 500, data)
        self.assertEqual(data["code"], "INTERNAL_SERVER_ERROR")
        self.assertNotIn("synthetic", str(data))
        self.assertEqual(self.counts(), (0, 0))

    async def test_duplicate_detail_returns_integrity_error(self):
        _, _, created = await self.create_grade()
        self.session.add(PerformanceSeats(seat_id2=created["data"]["seat_id"], seat_seq="A01", status="CUSTOM"))
        self.session.commit()
        status, _, data = await self.request("GET", "/v1/performances/10/seats/A01")
        self.assertEqual((status, data["code"]), (500, "SEAT_LOOKUP_INTEGRITY_ERROR"))

    async def test_read_preserves_unconfigured_legacy_rows(self):
        grade = SeatsInfoModel(perf_id=10)
        self.session.add(grade)
        self.session.flush()
        self.session.add(PerformanceSeats(seat_id2=grade.seat_id, seat_seq=None, status="UNCONFIGURED"))
        self.session.commit()
        status, _, data = await self.request("GET", "/v1/performances/10/seats")
        self.assertEqual(status, 200)
        item = data["data"]["items"][0]
        self.assertIsNone(item["grade"])
        self.assertIsNone(item["price"])
        self.assertIsNone(item["seat_seq"])

    async def test_owned_reservation_and_purchase_amount_are_stable(self):
        _, _, created = await self.create_grade()
        self.session.execute(PerformanceSeats.__table__.update().values(reserv_id=100, status="RESERVED"))
        self.session.commit()
        seat_id = created["data"]["seat_id"]
        await self.request("PATCH", f"/v1/performances/10/seat-infos/{seat_id}", {"price": 70000}, "owner")
        status, _, data = await self.request("GET", "/v1/reservations/100/seats", token="owner")
        self.assertEqual(status, 200, data)
        self.assertEqual(Decimal(data["data"]["purchase_price"]), Decimal("110000.00"))
        self.assertEqual(data["data"]["quantity"], 2)
        self.assertEqual(len(data["data"]["items"]), 2)
        self.assertTrue(all(item["price"] == 70000 for item in data["data"]["items"]))
        self.assertNotIn("user_id", str(data))

    async def test_other_users_reservation_is_indistinguishable_from_missing(self):
        first = await self.request("GET", "/v1/reservations/100/seats", token="other")
        second = await self.request("GET", "/v1/reservations/999/seats", token="other")
        self.assertEqual((first[0], second[0]), (404, 404))
        self.assertEqual(first[2]["code"], second[2]["code"])
        self.assertEqual(first[2]["message"], second[2]["message"])
        self.assertEqual((await self.request("GET", "/v1/reservations/100/seats"))[0], 401)

    async def test_cross_performance_reservation_link_fails_safely(self):
        await self.create_grade(perf_id=20, token="other")
        self.session.execute(PerformanceSeats.__table__.update().values(reserv_id=100))
        self.session.commit()
        status, _, data = await self.request("GET", "/v1/reservations/100/seats", token="owner")
        self.assertEqual((status, data["code"]), (500, "RESERVATION_SEAT_INTEGRITY_ERROR"))

    def test_openapi_and_six_routes(self):
        paths = self.app.openapi()["paths"]
        self.assertEqual(sum(len(ops) for ops in paths.values()), 6)
        self.assertIn("post", paths["/v1/performances/{perf_id}/seat-infos"])
        self.assertIn("patch", paths["/v1/performances/{perf_id}/seat-infos/{seat_id}"])



    async def test_legacy_grade_read_does_not_apply_new_creation_price_rule(self):
        for price in (None, 30000):
            grade = SeatsInfoModel(perf_id=10, name=None, total_seat=None, price=price)
            self.session.add(grade)
            self.session.commit()
            status, _, data = await self.request("GET", f"/v1/performances/10/seat-infos/{grade.seat_id}")
            self.assertEqual(status, 200, data)
            self.assertEqual(data["data"]["price"], price)
            self.assertIsNone(data["data"]["total_seat"])


    async def test_admin_policy_can_be_restricted(self):
        self.app.state.catalog_policy = CatalogPolicy(admin_can_manage_all=False)
        self.assertEqual((await self.create_grade(token="admin"))[0], 403)
        self.assertEqual(self.counts(), (0, 0))

    async def test_common_app_creates_and_reads_seats_with_registered_wiring(self):
        from asyncticket.main import create_app
        from asyncticket.shared.core.database import get_db

        app = create_app(authenticator=Authenticator())
        app.dependency_overrides[get_db] = self.test_db
        status, _, created = await asgi_request(
            app, "POST", "/v1/performances/10/seat-infos", self.body, "owner",
            raise_server_exceptions=False,
        )
        self.assertEqual(status, 201, created)
        status, _, data = await asgi_request(
            app, "GET", "/v1/performances/10/seats", raise_server_exceptions=False,
        )
        self.assertEqual(status, 200, data)
        self.assertEqual([item["seat_seq"] for item in data["data"]["items"]], ["A01", "A02"])
        self.assertEqual(self.counts(), (1, 2))


if __name__ == "__main__":
    unittest.main()
