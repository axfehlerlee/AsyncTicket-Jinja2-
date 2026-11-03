"""Repository SQL and complete ASGI reads; no PostgreSQL or production service access."""

import ast
import json
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy import BigInteger, Column, Integer, MetaData, Table, create_engine, event, select, func
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value
from sqlalchemy.schema import CreateTable

from asyncticket.dependencies import get_performance_service, get_show_service
from asyncticket.main import create_app
from asyncticket.performances.application.service import PerformanceApplicationService
from asyncticket.performances.infrastructure.models import PerformanceModel
from asyncticket.performances.infrastructure.repositories import SqlAlchemyPerformanceRepository
from asyncticket.shows.application.service import ShowApplicationService
from asyncticket.shows.domain.show import Show
from asyncticket.shows.infrastructure.models import ShowModel
from asyncticket.shows.infrastructure.repositories import SqlAlchemyShowRepository
from asyncticket.shared.domain.catalog import CatalogActor, CatalogConflictError, CatalogPolicy
from asyncticket.shared.infrastructure.catalog import SqlAlchemyCatalogRelations, SqlAlchemyCatalogUnitOfWork

UTC = timezone.utc
T0 = datetime(2026, 11, 3, tzinfo=UTC)


class AsyncSessionAdapter:
    """Run production SELECT statements against an isolated, synchronous test database."""

    def __init__(self, session: Session) -> None:
        self.session = session

    async def scalar(self, statement):
        return self._normalize(self.session.scalar(statement))

    async def scalars(self, statement):
        return [self._normalize(model) for model in self.session.scalars(statement)]

    @staticmethod
    def _normalize(model):
        # SQLite drops timezone information; only this test adapter restores the
        # UTC fixture convention. Production keeps PostgreSQL TIMESTAMPTZ values.
        if isinstance(model, (ShowModel, PerformanceModel)):
            for name in model.__table__.c.keys():
                value = getattr(model, name)
                if isinstance(value, datetime) and value.utcoffset() is None:
                    set_committed_value(model, name, value.replace(tzinfo=UTC))
        return model

    async def execute(self, statement):
        if statement.is_insert or statement.is_update:
            # PostgreSQL normalizes aware timestamps; SQLite does not. Normalize
            # only the test bind values so the fixture keeps the same instants.
            timestamps = {
                key: value.astimezone(UTC)
                for key, value in statement.compile().params.items()
                if isinstance(value, datetime) and value.utcoffset() is not None
            }
            if timestamps:
                statement = statement.values(**timestamps)
        result = self.session.execute(statement)
        class WriteResult:
            def mappings(self):
                return self

            def one(self):
                return {
                    key: value.replace(tzinfo=UTC)
                    if isinstance(value, datetime) and value.utcoffset() is None else value
                    for key, value in result.mappings().one().items()
                }
        return WriteResult()

    async def commit(self):
        self.session.commit()

    async def rollback(self):
        self.session.rollback()


class FixtureAuthenticator:
    """Test tokens have no production implementation or installation path."""

    async def authenticate(self, token):
        return {
            "seller": CatalogActor(1, "SELLER"), "other": CatalogActor(2, "SELLER"),
            "buyer": CatalogActor(3, "BUYER"), "admin": CatalogActor(4, "ADMIN"),
        }.get(token)


async def asgi_get(app, url: str) -> tuple[int, dict]:
    status, _, body = await asgi_request(app, "GET", url)
    return status, body


async def asgi_request(app, method, url, body=None, token=None):
    parts = urlsplit(url)
    messages = []

    async def receive():
        return {"type": "http.request", "body": json.dumps(body).encode() if body is not None else b"", "more_body": False}

    async def send(message):
        messages.append(message)

    await app(
        {
            "type": "http", "asgi": {"version": "3.0", "spec_version": "2.4"},
            "http_version": "1.1", "method": method, "scheme": "http",
            "path": parts.path, "raw_path": parts.path.encode(),
            "query_string": parts.query.encode(), "root_path": "",
            "headers": [(b"host", b"testserver"), (b"content-type", b"application/json")]
            + ([(b"authorization", f"Bearer {token}".encode())] if token else []),
            "client": ("127.0.0.1", 1234), "server": ("testserver", 80),
        }, receive, send,
    )
    status = next(m["status"] for m in messages if m["type"] == "http.response.start")
    body = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
    headers = next(m["headers"] for m in messages if m["type"] == "http.response.start")
    return status, dict(headers), json.loads(body) if body else None


class CatalogApiTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://")

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(connection, record):
            connection.execute("PRAGMA foreign_keys=ON")

        # Only this test metadata has minimal foreign-domain fixtures. Production
        # Base receives no placeholder venue/user models.
        self.metadata = MetaData()
        users = Table("users", self.metadata, Column("user_id", BigInteger, primary_key=True))
        venues = Table("venues", self.metadata, Column("venues_id", BigInteger, primary_key=True))
        ShowModel.__table__.to_metadata(self.metadata)
        PerformanceModel.__table__.to_metadata(self.metadata)
        # SQLite autogeneration requires INTEGER PRIMARY KEY. PostgreSQL DDL
        # remains BIGINT/BIGSERIAL, including in the DDL compilation test below.
        self.metadata.tables["shows"].c.show_id.type = BigInteger().with_variant(Integer, "sqlite")
        self.metadata.tables["performances"].c.perf_id.type = BigInteger().with_variant(Integer, "sqlite")
        Table("seats_info", self.metadata, Column("seat_id", Integer, primary_key=True), Column("perf_id", BigInteger))
        Table("reservations", self.metadata, Column("reserv_id", Integer, primary_key=True), Column("perf_id", BigInteger))
        self.metadata.create_all(self.engine)
        with self.engine.begin() as connection:
            connection.execute(users.insert(), [{"user_id": i} for i in range(1, 5)])
            connection.execute(venues.insert(), [{"venues_id": 1}, {"venues_id": 2}])
        self.session = Session(self.engine)
        self._seed("shows", [
            ShowModel(show_id=1, venues_id=1, user_id=1, title="Alpha 100%_Live",
                      description=None, performer=None, type="CONCERT", runtime=None, created_at=T0),
            ShowModel(show_id=2, venues_id=2, user_id=1, title="Beta",
                      description="소개", performer="출연자", type="CLASS", runtime=60, created_at=T0),
            ShowModel(show_id=3, venues_id=1, user_id=1, title="alpha ordinary",
                      description=None, performer=None, type="CONCERT", runtime=120, created_at=T0),
        ])
        # Boundaries for 2026-11-03 KST: UTC Nov 2 15:00 <= start < Nov 3 15:00.
        starts = [T0 - timedelta(hours=9, seconds=1), T0 - timedelta(hours=9),
                  T0 + timedelta(hours=15, seconds=-1), T0 + timedelta(hours=15)]
        self._seed("performances", [
            PerformanceModel(perf_id=10+i, show_id=1, round_number=i+1,
                             starts_at=start, ends_at=start+timedelta(hours=2),
                             booking_opens_at=start-timedelta(days=1),
                             booking_closes_at=start-timedelta(hours=1),
                             max_tickets_per_user=3, status="SCHEDULED")
            for i, start in enumerate(starts)
        ])
        adapter = AsyncSessionAdapter(self.session)
        self.relations = SqlAlchemyCatalogRelations(adapter)
        self.uow = SqlAlchemyCatalogUnitOfWork(adapter)
        self.policy = CatalogPolicy()
        self.shows = ShowApplicationService(SqlAlchemyShowRepository(adapter), self.relations, self.uow, self.policy)
        self.performances = PerformanceApplicationService(SqlAlchemyPerformanceRepository(adapter), self.shows, self.relations, self.uow, self.policy)
        self.app = create_app(authenticator=FixtureAuthenticator())
        self.app.dependency_overrides[get_show_service] = lambda: self.shows
        self.app.dependency_overrides[get_performance_service] = lambda: self.performances

    def _seed(self, name: str, models: list) -> None:
        table = self.metadata.tables[name]
        rows = [{column.name: getattr(model, column.name) for column in table.columns}
                for model in models]
        with self.engine.begin() as connection:
            connection.execute(table.insert(), rows)

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    async def test_show_list_stable_pagination_and_total(self) -> None:
        status, body = await asgi_get(self.app, "/v1/shows?page=2&size=1")
        self.assertEqual(status, 200)
        self.assertEqual((body["page"], body["size"], body["total"]), (2, 1, 3))
        self.assertEqual([item["show_id"] for item in body["items"]], [2])

    async def test_show_filters_and_literal_wildcards(self) -> None:
        status, body = await asgi_get(self.app, "/v1/shows?keyword=100%25_&type=CONCERT&venues_id=1")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["items"][0]["show_id"], 1)
        _, body = await asgi_get(self.app, "/v1/shows?keyword=ALPHA")
        self.assertEqual(body["total"], 2)

    async def test_empty_show_filters_and_out_of_range_page(self) -> None:
        for path in ("/v1/shows?venues_id=999", "/v1/shows?page=99"):
            status, body = await asgi_get(self.app, path)
            self.assertEqual(status, 200)
            self.assertEqual(body["items"], [])

    async def test_public_detail_excludes_owner_and_preserves_nulls(self) -> None:
        status, body = await asgi_get(self.app, "/v1/shows/1")
        self.assertEqual(status, 200)
        self.assertNotIn("user_id", body)
        self.assertIsNone(body["description"])
        self.assertIsNone(body["runtime"])
        self.assertIsNone(body["updated_at"])

    async def test_unknown_resources_are_404(self) -> None:
        for path in ("/v1/shows/999", "/v1/performances/999", "/v1/shows/999/performances"):
            status, body = await asgi_get(self.app, path)
            self.assertEqual(status, 404, path)
            self.assertEqual(body["detail"]["code"], "RESOURCE_NOT_FOUND")

    async def test_invalid_inputs_are_422(self) -> None:
        for path in (
            "/v1/shows?page=0", "/v1/shows?size=101", "/v1/shows?size=-1",
            "/v1/shows?venues_id=0", "/v1/shows/0", "/v1/shows/abc",
            "/v1/performances/-1", "/v1/shows/1/performances?date=invalid",
            "/v1/shows/1/performances?date=2026-02-30",
            "/v1/shows/1/performances?date=0",
            "/v1/shows/1/performances?date=2026-11-03T00:00:00",
            "/v1/shows/1/performances?date=9999-12-31",
            "/v1/shows?page=999999999999999999999999999",
            "/v1/shows/9223372036854775808", "/v1/performances/9223372036854775808",
            "/v1/shows?venues_id=9223372036854775808",
        ):
            status, _ = await asgi_get(self.app, path)
            self.assertEqual(status, 422, path)

    async def test_kst_date_filter_includes_start_excludes_next_midnight(self) -> None:
        status, body = await asgi_get(self.app, "/v1/shows/1/performances?date=2026-11-03")
        self.assertEqual(status, 200)
        self.assertEqual([item["perf_id"] for item in body["items"]], [11, 12])

    async def test_performance_list_scopes_to_parent(self) -> None:
        status, body = await asgi_get(self.app, "/v1/shows/2/performances")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"items": []})
        _, body = await asgi_get(self.app, "/v1/shows/1/performances")
        self.assertEqual([item["perf_id"] for item in body["items"]], [10, 11, 12, 13])

    async def test_performance_detail_preserves_stored_policy(self) -> None:
        status, body = await asgi_get(self.app, "/v1/performances/11")
        self.assertEqual(status, 200)
        self.assertEqual((body["show_id"], body["round_number"]), (1, 2))
        self.assertEqual(body["max_tickets_per_user"], 3)
        self.assertEqual(body["status"], "SCHEDULED")

    async def test_gets_do_not_change_rows(self) -> None:
        before = [tuple(row) for row in self.session.execute(ShowModel.__table__.select())]
        await asgi_get(self.app, "/v1/shows")
        await asgi_get(self.app, "/v1/shows/1/performances")
        self.assertEqual(before, [tuple(row) for row in self.session.execute(ShowModel.__table__.select())])
        self.assertFalse(self.session.new or self.session.dirty or self.session.deleted)

    async def test_repositories_return_domain_entities(self) -> None:
        self.assertIsInstance(await self.shows.find_by_id(1), Show)

    def test_postgresql_ddl_preserves_foreign_keys_and_types(self) -> None:
        show_ddl = str(CreateTable(self.metadata.tables["shows"]).compile(dialect=postgresql.dialect()))
        perf_ddl = str(CreateTable(self.metadata.tables["performances"]).compile(dialect=postgresql.dialect()))
        self.assertIn("TIMESTAMP WITH TIME ZONE", show_ddl)
        self.assertIn("FOREIGN KEY(venues_id) REFERENCES venues (venues_id)", show_ddl)
        self.assertIn("FOREIGN KEY(show_id) REFERENCES shows (show_id)", perf_ddl)
        self.assertIn("DEFAULT 3", perf_ddl)

    def test_layer_boundaries(self) -> None:
        src = Path(__file__).resolve().parents[1] / "src/asyncticket"
        for feature in ("shows", "performances"):
            for layer in ("domain", "application", "presentation"):
                for path in (src / feature / layer).glob("*.py"):
                    tree = ast.parse(path.read_text(encoding="utf-8"))
                    imports = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
                    imports += [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
                    self.assertFalse(any(".infrastructure" in name for name in imports), path)
                    if layer == "domain":
                        self.assertFalse(any(name.split(".")[0] in ("fastapi", "sqlalchemy", "pydantic") for name in imports), path)

    async def test_openapi_matches_all_ten_operations(self) -> None:
        status, body = await asgi_get(self.app, "/openapi.json")
        self.assertEqual(status, 200)
        self.assertEqual(set(body["paths"]), {
            "/v1/shows", "/v1/shows/{show_id}",
            "/v1/shows/{show_id}/performances", "/v1/performances/{perf_id}",
        })
        self.assertEqual(sum(len(operations) for operations in body["paths"].values()), 10)
        self.assertEqual(
            {(method, path) for path, operations in body["paths"].items() for method in operations},
            {
                ("get", "/v1/shows"), ("post", "/v1/shows"),
                ("get", "/v1/shows/{show_id}"), ("patch", "/v1/shows/{show_id}"),
                ("delete", "/v1/shows/{show_id}"),
                ("get", "/v1/shows/{show_id}/performances"),
                ("post", "/v1/shows/{show_id}/performances"),
                ("get", "/v1/performances/{perf_id}"),
                ("patch", "/v1/performances/{perf_id}"),
                ("delete", "/v1/performances/{perf_id}"),
            },
        )

    @staticmethod
    def show_body(**changes):
        return {"venues_id": 1, "title": "새 공연", "description": "소개",
                "performer": "출연자", "type": "CONCERT", "runtime": 120, **changes}

    @staticmethod
    def performance_body(**changes):
        return {
            "round_number": 7, "starts_at": "2026-11-07T19:00:00+09:00",
            "ends_at": "2026-11-07T21:00:00+09:00",
            "booking_opens_at": "2026-10-30T10:00:00+09:00",
            "booking_closes_at": "2026-11-07T18:00:00+09:00", "status": "SCHEDULED",
            **changes,
        }

    async def test_show_create_update_delete_contract(self) -> None:
        status, headers, body = await asgi_request(
            self.app, "POST", "/v1/shows", self.show_body(), "seller",
        )
        self.assertEqual(status, 201, body)
        show_id = body["show_id"]
        self.assertEqual(headers[b"location"].decode(), f"/v1/shows/{show_id}")
        self.assertNotIn("user_id", body)
        owner = self.session.scalar(select(ShowModel.user_id).where(ShowModel.show_id == show_id))
        self.assertEqual(owner, 1)
        status, _, body = await asgi_request(
            self.app, "PATCH", f"/v1/shows/{show_id}",
            {"title": "변경 공연", "description": None, "runtime": None, "venues_id": 2}, "seller",
        )
        self.assertEqual(status, 200, body)
        self.assertEqual((body["title"], body["venues_id"]), ("변경 공연", 2))
        self.assertIsNone(body["description"])
        self.assertIsNone(body["runtime"])
        self.assertEqual(body["performer"], "출연자")
        self.assertIsNotNone(body["updated_at"])
        status, headers, body = await asgi_request(self.app, "DELETE", f"/v1/shows/{show_id}", token="seller")
        self.assertEqual(status, 204)
        self.assertIsNone(body)
        self.assertNotIn(b"content-type", headers)
        self.assertEqual((await asgi_get(self.app, f"/v1/shows/{show_id}"))[0], 404)

    async def test_performance_create_update_delete_contract(self) -> None:
        status, headers, body = await asgi_request(
            self.app, "POST", "/v1/shows/2/performances", self.performance_body(), "seller",
        )
        self.assertEqual(status, 201, body)
        perf_id = body["perf_id"]
        self.assertEqual(headers[b"location"].decode(), f"/v1/performances/{perf_id}")
        self.assertEqual((body["show_id"], body["max_tickets_per_user"]), (2, 3))
        status, _, body = await asgi_request(
            self.app, "PATCH", f"/v1/performances/{perf_id}",
            {"booking_closes_at": "2026-11-07T18:30:00+09:00", "round_number": 8}, "seller",
        )
        self.assertEqual(status, 200, body)
        self.assertEqual(body["round_number"], 8)
        self.assertEqual(body["status"], "SCHEDULED")
        self.assertEqual(datetime.fromisoformat(body["booking_closes_at"]), datetime.fromisoformat("2026-11-07T18:30:00+09:00"))
        status, headers, body = await asgi_request(self.app, "DELETE", f"/v1/performances/{perf_id}", token="seller")
        self.assertEqual(status, 204)
        self.assertIsNone(body)
        self.assertNotIn(b"content-type", headers)
        self.assertEqual((await asgi_get(self.app, f"/v1/performances/{perf_id}"))[0], 404)

    def write_requests(self):
        return [
            ("POST", "/v1/shows", self.show_body()),
            ("PATCH", "/v1/shows/1", {"title": "변경"}),
            ("DELETE", "/v1/shows/3", None),
            ("POST", "/v1/shows/2/performances", self.performance_body()),
            ("PATCH", "/v1/performances/11", {"round_number": 8}),
            ("DELETE", "/v1/performances/11", None),
        ]

    async def test_all_six_writes_require_verified_authentication(self) -> None:
        for method, url, body in self.write_requests():
            for token in (None, "invalid"):
                status, headers, result = await asgi_request(self.app, method, url, body, token)
                self.assertEqual(status, 401, (url, result))
                self.assertEqual(headers[b"www-authenticate"], b"Bearer")
                self.assertEqual(result["detail"]["code"], "AUTHENTICATION_REQUIRED")

    async def test_all_six_writes_forbid_buyer(self) -> None:
        for method, url, body in self.write_requests():
            status, _, result = await asgi_request(self.app, method, url, body, "buyer")
            self.assertEqual(status, 403, (url, result))

    async def test_seller_cannot_manage_other_sellers_data(self) -> None:
        for method, url, body in self.write_requests()[1:]:
            status, _, result = await asgi_request(self.app, method, url, body, "other")
            self.assertEqual(status, 403, (url, result))

    async def test_admin_can_manage_existing_show_under_explicit_policy(self) -> None:
        status, _, result = await asgi_request(self.app, "PATCH", "/v1/shows/1", {"title": "관리자 변경"}, "admin")
        self.assertEqual(status, 200, result)
        self.assertEqual(result["title"], "관리자 변경")
        self.assertEqual(self.session.scalar(select(ShowModel.user_id).where(ShowModel.show_id == 1)), 1)

    async def test_missing_common_authentication_module_never_grants_access(self) -> None:
        app = create_app()
        status, _, result = await asgi_request(app, "POST", "/v1/shows", self.show_body(), "anything")
        self.assertEqual(status, 503)
        self.assertEqual(result["detail"]["code"], "INTEGRATION_UNAVAILABLE")

    async def test_writes_return_404_for_missing_targets(self) -> None:
        cases = [
            ("POST", "/v1/shows", self.show_body(venues_id=999)),
            ("PATCH", "/v1/shows/999", {"title": "없음"}),
            ("DELETE", "/v1/shows/999", None),
            ("POST", "/v1/shows/999/performances", self.performance_body()),
            ("PATCH", "/v1/performances/999", {"status": "SCHEDULED"}),
            ("DELETE", "/v1/performances/999", None),
            ("PATCH", "/v1/shows/3", {"venues_id": 999}),
        ]
        for method, url, body in cases:
            status, _, result = await asgi_request(self.app, method, url, body, "seller")
            self.assertEqual(status, 404, (url, result))

    async def test_partial_updates_reject_empty_null_immutable_and_unknown_fields(self) -> None:
        cases = [
            ("/v1/shows/1", {}), ("/v1/shows/1", {"title": None}),
            ("/v1/shows/1", {"venues_id": None}), ("/v1/shows/1", {"user_id": 2}),
            ("/v1/shows/1", {"created_at": "2026-11-03"}),
            ("/v1/shows/1", {"unknown": "x"}), ("/v1/shows/1", {"runtime": -1}),
            ("/v1/performances/11", {}), ("/v1/performances/11", {"status": None}),
            ("/v1/performances/11", {"show_id": 2}),
            ("/v1/performances/11", {"max_tickets_per_user": None}),
        ]
        for url, body in cases:
            status, _, result = await asgi_request(self.app, "PATCH", url, body, "seller")
            self.assertEqual(status, 422, (url, body, result))
            self.assertEqual(result["detail"]["code"], "VALIDATION_ERROR")

    async def test_create_input_fields_lengths_and_types(self) -> None:
        for changes in ({"title": " "}, {"title": "x" * 256}, {"type": ""},
                        {"runtime": 0}, {"venues_id": True}, {"user_id": 2},
                        {"show_id": 99}, {"performer": "x" * 256}):
            status, _, result = await asgi_request(self.app, "POST", "/v1/shows", self.show_body(**changes), "seller")
            self.assertEqual(status, 422, (changes, result))

    async def test_performance_time_order_and_timezone_validation(self) -> None:
        cases = [
            {"starts_at": "2026-11-07T19:00:00"}, {"starts_at": 1794045600},
            {"ends_at": "2026-11-07T18:00:00+09:00"},
            {"booking_opens_at": "2026-11-07T18:00:00+09:00"},
            {"booking_closes_at": "2026-11-07T20:00:00+09:00"},
            {"round_number": 0}, {"max_tickets_per_user": 0}, {"status": ""},
        ]
        for changes in cases:
            status, _, result = await asgi_request(self.app, "POST", "/v1/shows/2/performances", self.performance_body(**changes), "seller")
            self.assertEqual(status, 422, (changes, result))
        status, _, result = await asgi_request(
            self.app, "PATCH", "/v1/performances/11",
            {"booking_closes_at": "2026-11-07T20:00:00+09:00"}, "seller",
        )
        self.assertEqual(status, 422, result)

    async def test_booking_can_close_exactly_at_performance_start(self) -> None:
        status, _, result = await asgi_request(
            self.app, "POST", "/v1/shows/2/performances",
            self.performance_body(booking_closes_at="2026-11-07T19:00:00+09:00"), "seller",
        )
        self.assertEqual(status, 201, result)

    async def test_show_link_and_round_conflicts_return_409(self) -> None:
        cases = [
            ("PATCH", "/v1/shows/1", {"venues_id": 2}),
            ("DELETE", "/v1/shows/1", None),
            ("POST", "/v1/shows/1/performances", self.performance_body(round_number=1)),
            ("PATCH", "/v1/performances/11", {"round_number": 1}),
        ]
        for method, url, body in cases:
            status, _, result = await asgi_request(self.app, method, url, body, "seller")
            self.assertEqual(status, 409, (url, result))
        self.assertEqual((await asgi_get(self.app, "/v1/performances/11"))[1]["round_number"], 2)

    async def test_linked_seats_block_performance_changes_and_deletion(self) -> None:
        self.session.execute(self.metadata.tables["seats_info"].insert().values(seat_id=1, perf_id=11))
        self.session.commit()
        for method, body in (("PATCH", {"status": "CANCELED"}), ("DELETE", None)):
            status, _, result = await asgi_request(self.app, method, "/v1/performances/11", body, "seller")
            self.assertEqual(status, 409, result)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(self.metadata.tables["seats_info"])), 1)

    async def test_linked_reservations_block_performance_changes_and_deletion(self) -> None:
        self.session.execute(self.metadata.tables["reservations"].insert().values(reserv_id=1, perf_id=11))
        self.session.commit()
        for method, body in (("PATCH", {"max_tickets_per_user": 2}), ("DELETE", None)):
            status, _, result = await asgi_request(self.app, method, "/v1/performances/11", body, "seller")
            self.assertEqual(status, 409, result)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(self.metadata.tables["reservations"])), 1)

    async def test_commit_failure_rolls_back_insert(self) -> None:
        before = self.session.scalar(select(func.count()).select_from(ShowModel))
        adapter = AsyncSessionAdapter(self.session)
        class RejectCommit:
            async def commit(self):
                raise CatalogConflictError("검증용 커밋 실패")

            async def rollback(self):
                await adapter.rollback()
        self.shows._uow = RejectCommit()
        status, _, result = await asgi_request(self.app, "POST", "/v1/shows", self.show_body(), "seller")
        self.assertEqual(status, 409, result)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(ShowModel)), before)

    async def test_configurable_status_allowlist_is_applied(self) -> None:
        self.performances._policy = CatalogPolicy(performance_statuses=frozenset({"SCHEDULED"}))
        status, _, result = await asgi_request(self.app, "POST", "/v1/shows/2/performances", self.performance_body(status="UNCONFIRMED"), "seller")
        self.assertEqual(status, 422, result)


if __name__ == "__main__":
    unittest.main()
