"""응용 계층: 공연 소유권, 회차 규칙, 연결 데이터와 트랜잭션을 조율한다."""

from dataclasses import asdict
from datetime import date, datetime, time, timedelta, timezone

from asyncticket.performances.domain.performance import Performance, PerformanceNotFoundError
from asyncticket.performances.domain.repositories import PerformanceRepository
from asyncticket.shared.domain.catalog import (
    CatalogActor, CatalogConflictError, CatalogPolicy, CatalogRelations, CatalogUnitOfWork,
)
from asyncticket.shared.domain.catalog_validation import validate_performance
from asyncticket.shows.application.service import ShowApplicationService

KST = timezone(timedelta(hours=9), name="Asia/Seoul")


class PerformanceApplicationService:
    def __init__(
        self, repository: PerformanceRepository, show_service: ShowApplicationService,
        relations: CatalogRelations, unit_of_work: CatalogUnitOfWork, policy: CatalogPolicy,
    ) -> None:
        self._repository = repository
        self._show_service = show_service
        self._relations = relations
        self._uow = unit_of_work
        self._policy = policy

    async def find_by_id(self, perf_id: int, *, for_update: bool = False) -> Performance:
        performance = await self._repository.find_by_id(perf_id, for_update=for_update)
        if performance is None:
            raise PerformanceNotFoundError("공연 회차를 찾을 수 없습니다.")
        return performance

    async def find_all(self, show_id: int, on_date: date | None) -> list[Performance]:
        await self._show_service.find_by_id(show_id)
        starts_from = starts_until = None
        if on_date is not None:
            # 한국 날짜의 자정 이상~다음 자정 미만을 UTC 조회 범위로 바꾼다.
            starts_from = datetime.combine(on_date, time.min, tzinfo=KST).astimezone(timezone.utc)
            starts_until = starts_from + timedelta(days=1)
        return await self._repository.find_all(show_id, starts_from, starts_until)

    async def create(
        self, show_id: int, values: dict[str, object], actor: CatalogActor,
    ) -> Performance:
        try:
            # 같은 공연의 회차 변경을 직렬화한 뒤 회차 번호 중복을 검사한다.
            await self._show_service.authorize_owner(show_id, actor)
            validate_performance(values, self._policy)
            if await self._repository.round_exists(show_id, values["round_number"]):
                raise CatalogConflictError("공연 안에서 회차 번호가 중복됩니다.")
            performance = await self._repository.create({**values, "show_id": show_id})
            await self._uow.commit()
            return performance
        except Exception:
            await self._uow.rollback()
            raise

    async def _authorize(self, perf_id: int, actor: CatalogActor) -> Performance:
        self._policy.authorize(actor)
        current = await self.find_by_id(perf_id)
        await self._show_service.authorize_owner(current.show_id, actor)
        return await self.find_by_id(perf_id, for_update=True)

    async def _has_links(self, perf_id: int) -> bool:
        return (
            await self._relations.performance_has_seats(perf_id)
            or await self._relations.performance_has_reservations(perf_id)
        )

    async def update(
        self, perf_id: int, changes: dict[str, object], actor: CatalogActor,
    ) -> Performance:
        try:
            performance = await self._authorize(perf_id, actor)
            before = asdict(performance)
            merged = {**before, **changes}
            # PATCH 입력 일부만 보지 않고, 기존 값과 합친 전체 시간순서를 검사한다.
            validate_performance(merged, self._policy)
            if await self._repository.round_exists(
                performance.show_id, merged["round_number"], exclude_id=perf_id,
            ):
                raise CatalogConflictError("공연 안에서 회차 번호가 중복됩니다.")
            has_changes = any(before[key] != value for key, value in changes.items())
            if has_changes and self._policy.block_performance_changes_with_links:
                if await self._has_links(perf_id):
                    raise CatalogConflictError("좌석 구성 또는 예매가 연결된 회차는 변경할 수 없습니다.")
            performance = await self._repository.update(perf_id, changes)
            await self._uow.commit()
            return performance
        except Exception:
            await self._uow.rollback()
            raise

    async def delete(self, perf_id: int, actor: CatalogActor) -> None:
        try:
            await self._authorize(perf_id, actor)
            if await self._has_links(perf_id):
                raise CatalogConflictError("좌석 구성 또는 예매가 연결된 회차는 삭제할 수 없습니다.")
            # 연결 데이터의 취소·환불·연쇄 삭제는 이 API가 수행하지 않는다.
            await self._repository.delete(perf_id)
            await self._uow.commit()
        except Exception:
            await self._uow.rollback()
            raise
