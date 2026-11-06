"""전용 로컬 DB opt-in 검사. 테스트별 임시 스키마만 생성·삭제한다."""

import asyncio
from datetime import datetime, timedelta, timezone
import os
import re
from pathlib import Path
import sys
import uuid
import unittest

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import BigInteger, Column, DateTime, MetaData, Table, insert, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "seat_queries"))
import test_configuration as configuration

from asyncticket.seats.application.service import PerformanceSeatService, SeatReservationConflictError
from asyncticket.seats.domain.enums import SeatGrade, SeatStatus
from asyncticket.seats.infrastructure.models import PerformanceSeats, SeatsInfoModel
from asyncticket.seats.infrastructure.repositories import SqlAlchemyPerformanceSeatRepository, SqlAlchemySeatInfoRepository
from asyncticket.seats.presentation.router import router
from asyncticket.shared.core.exception_handlers import register_exception_handlers
from asyncticket.shared.domain.catalog import CatalogActor
from asyncticket.shared.presentation.catalog_auth import get_current_catalog_actor
from asyncticket.shared.presentation.catalog_http import register_catalog_errors
from asyncticket.wiring.seats import wire_dependencies
from asyncticket.wiring.performance_seats import wire_dependencies as wire_queries

URL = os.getenv("ASYNCTICKET_TEST_DATABASE_URL")


@unittest.skipUnless(URL, "전용 로컬 PostgreSQL URL을 명시해야 실행합니다")
class SeatPostgresTests(configuration.SeatConfigurationTests):
    async def asyncSetUp(self):
        url = make_url(URL)
        if (url.drivername != "postgresql+asyncpg"
                or url.host not in ("127.0.0.1", "localhost", "::1")
                or not url.database
                or url.query
                or not re.search(r"(?:^|[_-])(?:test|local)(?:$|[_-])", url.database.lower())):
            self.fail("이름에 test/local 구분 단어가 있는 전용 로컬 DB만 사용하세요. URL 쿼리는 허용하지 않습니다.")
        self.schema = "seat_test_" + uuid.uuid4().hex
        self.admin_engine = create_async_engine(url, echo=False, connect_args={
            "server_settings": {"statement_timeout": "10000", "lock_timeout": "3000"},
        })
        self.addAsyncCleanup(self.admin_engine.dispose)
        async with self.admin_engine.begin() as conn:
            await conn.execute(text(f'CREATE SCHEMA "{self.schema}"'))
        self.addAsyncCleanup(self._drop_schema)
        self.engine = create_async_engine(url, echo=False, connect_args={
            "server_settings": {"search_path": self.schema, "statement_timeout": "10000",
                                "lock_timeout": "3000"},
        })
        self.addAsyncCleanup(self.engine.dispose)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        metadata = MetaData()
        shows = Table("shows", metadata, Column("show_id", BigInteger, primary_key=True),
                      Column("user_id", BigInteger, nullable=False))
        performances = Table("performances", metadata,
                             Column("perf_id", BigInteger, primary_key=True),
                             Column("show_id", BigInteger),
                             Column("booking_opens_at", DateTime(timezone=True)))
        reservations = Table("reservations", metadata,
                             Column("reserv_id", BigInteger, primary_key=True),
                             Column("perf_id", BigInteger, nullable=False))
        self.parent_stubs = []
        self.addCleanup(self._remove_parent_stubs)
        for name in ("performances", "reservations"):
            if name not in SeatsInfoModel.metadata.tables:
                self.parent_stubs.append(metadata.tables[name].to_metadata(SeatsInfoModel.metadata))
        SeatsInfoModel.__table__.to_metadata(metadata)
        PerformanceSeats.__table__.to_metadata(metadata)
        async with self.engine.begin() as conn:
            await conn.run_sync(metadata.create_all)
            await conn.execute(insert(shows), {"show_id": 1, "user_id": 7})
            await conn.execute(insert(performances), [
                {"perf_id": n, "show_id": 1,
                 "booking_opens_at": datetime.now(timezone.utc) + timedelta(days=1)}
                for n in (10, 20)
            ])
            await conn.execute(insert(reservations), [{"reserv_id": 1, "perf_id": 10},
                                                     {"reserv_id": 2, "perf_id": 20}])

        async def test_db():
            async with self.sessions() as session:
                yield session

        self.app = FastAPI()
        register_exception_handlers(self.app)
        register_catalog_errors(self.app)
        self.app.include_router(router)
        wire_dependencies(self.app, db_dependency=test_db)
        wire_queries(self.app, db_dependency=test_db)
        self.app.dependency_overrides[get_current_catalog_actor] = lambda: CatalogActor(7, "SELLER")
        self.client = AsyncClient(transport=ASGITransport(app=self.app, raise_app_exceptions=False),
                                  base_url="http://test")
        self.addAsyncCleanup(self.client.aclose)

    async def _drop_schema(self):
        # 이번 테스트가 UUID로 만든 임시 스키마만 삭제한다.
        if not re.fullmatch(r"seat_test_[0-9a-f]{32}", self.schema):
            raise RuntimeError("좌석 테스트 임시 스키마 외에는 삭제할 수 없습니다.")
        async with self.admin_engine.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA "{self.schema}" CASCADE'))

    async def _set_sale_started(self):
        async with self.engine.begin() as conn:
            await conn.execute(text("UPDATE performances SET booking_opens_at=:t WHERE perf_id=10"),
                               {"t": datetime.now(timezone.utc) - timedelta(days=1)})

    def _assignment_service(self, session):
        return PerformanceSeatService(SqlAlchemyPerformanceSeatRepository(session),
                                      SqlAlchemySeatInfoRepository(session))

    async def test_schema_matches_seat_foreign_keys_and_nullable_reservation(self):
        async with self.engine.connect() as conn:
            info = await conn.run_sync(lambda c: {
                "seat_columns": inspect(c).get_columns("performance_seats"),
                "seat_fks": inspect(c).get_foreign_keys("performance_seats"),
                "grade_fks": inspect(c).get_foreign_keys("seats_info"),
            })
        columns = {c["name"]: c for c in info["seat_columns"]}
        self.assertTrue(columns["reserv_id"]["nullable"])
        self.assertFalse(columns["seat_id2"]["nullable"])
        self.assertEqual({(tuple(f["constrained_columns"]), f["referred_table"],
                           tuple(f["referred_columns"])) for f in info["seat_fks"]},
                         {(("seat_id2",), "seats_info", ("seat_id",)),
                          (("reserv_id",), "reservations", ("reserv_id",))})
        self.assertEqual(info["grade_fks"][0]["referred_table"], "performances")

    async def test_database_strings_convert_to_domain_enums(self):
        await self._seed_configuration()
        async with self.sessions() as session:
            grade = await session.get(SeatsInfoModel, 101)
            seat = await session.get(PerformanceSeats, 1001)
            self.assertIs(grade.to_seat_info().name, SeatGrade.S)
            self.assertIs(seat.to_performance_seat().status, SeatStatus.AVAILABLE)

    async def test_database_rejects_orphan_foreign_keys(self):
        await self._seed_configuration()
        for values in ({"seat_id2": 999, "reserv_id": None},
                       {"seat_id2": 101, "reserv_id": 999}):
            with self.subTest(values=values):
                async with self.sessions() as session:
                    with self.assertRaises(IntegrityError):
                        await session.execute(insert(PerformanceSeats).values(
                            status="AVAILABLE", seat_seq="X01", **values))
                    await session.rollback()
        async with self.sessions() as session:
            with self.assertRaises(IntegrityError):
                await session.execute(insert(SeatsInfoModel).values(
                    perf_id=999, name="R석", total_seat=1, price=0))
            await session.rollback()

    async def test_assignment_rejects_wrong_performance_and_repeated_link(self):
        await self._seed_configuration()
        args = dict(perf_id=10, perf_seat_id=1001, reserv_id=1,
                    expected_status="AVAILABLE", reserved_status="RESERVED")
        async with self.sessions() as session:
            service = self._assignment_service(session)
            for override in ({"perf_id": 20}, {"reserv_id": 2}, {"reserv_id": 999},
                             {"expected_status": "OCCUPIED"}):
                with self.assertRaises(SeatReservationConflictError):
                    await service.assign_reservation(**(args | override))
            await service.assign_reservation(**args)
            with self.assertRaises(SeatReservationConflictError):
                await service.assign_reservation(**args)
            await session.commit()
        async with self.sessions() as session:
            seat = await session.get(PerformanceSeats, 1001)
            self.assertEqual((seat.reserv_id, seat.status), (1, "RESERVED"))

    async def test_uncommitted_reservation_visible_in_same_session_and_rollback(self):
        await self._seed_configuration()
        async with self.sessions() as session:
            await session.execute(text("INSERT INTO reservations(reserv_id,perf_id) VALUES (3,10)"))
            await session.flush()
            await self._assignment_service(session).assign_reservation(
                perf_id=10, perf_seat_id=1001, reserv_id=3,
                expected_status="AVAILABLE", reserved_status="RESERVED")
            await session.rollback()
        async with self.sessions() as session:
            self.assertEqual(await session.scalar(text("SELECT count(*) FROM reservations WHERE reserv_id=3")), 0)
            seat = await session.get(PerformanceSeats, 1001)
            self.assertEqual((seat.reserv_id, seat.status), (None, "AVAILABLE"))

    async def test_uncommitted_reservation_not_visible_in_other_session(self):
        await self._seed_configuration()
        async with self.sessions() as writer, self.sessions() as reader:
            await writer.execute(text("INSERT INTO reservations(reserv_id,perf_id) VALUES (3,10)"))
            with self.assertRaises(SeatReservationConflictError):
                await self._assignment_service(reader).assign_reservation(
                    perf_id=10, perf_seat_id=1001, reserv_id=3,
                    expected_status="AVAILABLE", reserved_status="RESERVED")
            await reader.rollback()
            await writer.rollback()

    async def test_two_concurrent_assignments_have_one_winner(self):
        await self._assert_concurrent_assignments(2)

    async def test_ten_concurrent_assignments_have_one_winner(self):
        await self._assert_concurrent_assignments(10)

    async def _assert_concurrent_assignments(self, workers):
        await self._seed_configuration()
        async with self.engine.begin() as conn:
            await conn.execute(text("INSERT INTO reservations(reserv_id,perf_id) VALUES (:r,10)"),
                               [{"r": n} for n in range(3, workers + 2)])
        ready = asyncio.Event()
        count = 0
        lock = asyncio.Lock()

        async def attempt(reserv_id):
            nonlocal count
            async with self.sessions() as session:
                async with lock:
                    count += 1
                    if count == workers:
                        ready.set()
                await ready.wait()
                try:
                    await self._assignment_service(session).assign_reservation(
                        perf_id=10, perf_seat_id=1001, reserv_id=reserv_id,
                        expected_status="AVAILABLE", reserved_status="RESERVED")
                    await session.commit()
                    return reserv_id
                except SeatReservationConflictError:
                    await session.rollback()
                    return None

        tasks = [asyncio.create_task(attempt(n)) for n in [1, *range(3, workers + 2)]]
        try:
            outcomes = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True), timeout=15,
            )
        finally:
            # 예상 밖 오류나 시간 초과에도 모든 세션이 닫힌 후 스키마를 정리한다.
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        self.assertFalse([type(item).__name__ for item in outcomes if isinstance(item, BaseException)])
        winners = [x for x in outcomes if x is not None]
        self.assertEqual(len(winners), 1)
        async with self.sessions() as session:
            seat = await session.get(PerformanceSeats, 1001)
            self.assertEqual((seat.reserv_id, seat.status), (winners[0], "RESERVED"))

    async def test_created_seats_are_readable_with_enum_and_slash_name(self):
        response = await self.client.post("/v1/performances/10/seat-infos", json={
            "name": "R석", "price": 0, "total_seat": 1, "seat_seqs": ["A/01"]})
        self.assertEqual(response.status_code, 201, response.text)
        for path in ("/v1/performances/10/seats", "/v1/performances/10/seats/A%2F01"):
            result = await self.client.get(path)
            self.assertEqual(result.status_code, 200, result.text)
            data = result.json()["data"]
            item = data["items"][0] if "items" in data else data
            self.assertEqual((item["grade"], item["status"], item["price"]),
                             ("R석", "AVAILABLE", 0))
