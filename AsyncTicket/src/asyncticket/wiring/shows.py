# [A팀에서 wiring을 두는 이유]
# A팀은 기능별로 presentation / application / domain / infrastructure 4계층을 사용한다.
# wiring은 5번째 업무 계층이 아니라, 각 계층에서 사용할 실제 객체를 조립하는 위치다.
# domain은 좌석·공연 등의 업무 규칙과 저장소 계약을 정의한다.
# infrastructure는 SQLAlchemy로 PostgreSQL에 접근하고 ORM ↔ 도메인 객체를 변환한다.
# application은 저장소를 통해 정보를 가져와 도메인 규칙을 실행하고 작업 흐름을 조율한다.
# presentation은 HTTP 입력·응답을 다루고 Depends로 필요한 서비스를 요청한다.
# wiring은 이 서비스에 어떤 저장소와 DB 세션을 넣을지 선택한다. 업무 규칙·SQL을 여기에 쓰지 않는다.
# shared의 공통 세션·정책은 가져다 사용하고, 이 연결을 위해 shared 파일을 수정하지 않는다.
#
# [두 종류의 흐름을 구분하기]
# 객체 조립: DB 세션 → 저장소 객체 생성 → 서비스 생성자에 저장소 전달 → 라우터에 서비스 제공.
# 업무 실행: 라우터 → 서비스 → 저장소의 조회/저장 메서드 → DB. 규칙 판단은 도메인에 맡긴다.
# 주입할 때 객체를 만드는 것과, 이후 그 객체의 메서드를 호출하는 것은 다른 단계다.
# 실제 SQLAlchemy 구현을 아는 부분을 조립 위치에 모아 서비스와 DB 구현의 결합을 줄인다.
# 테스트에서는 같은 저장소 계약을 지키는 테스트용 구현으로 교체할 수 있다.
#
# [이 파일: 공연 담당 영역의 기존 연결 함수]
# get_catalog_policy는 앱에 설정된 공연 권한·운영 정책을 가져온다.
# create_show_service는 get_db가 제공하는 세션으로 공연 저장소·연결 조회·트랜잭션 객체를 생성한다.
# 이 객체들을 ShowApplicationService에 넣고 라우터에 반환한다.
# 현재 공연 라우터는 provide_show_service를 요청하며, 공용 wiring에서 생성 함수를 연결한다.
# 이 파일은 기존 연결을 옮긴 것이며, 정은님이 공연의 업무 규칙을 수정하는 위치가 아니다.

"""공연 서비스의 주입 계약과 실제 객체 조립을 한곳에서 관리한다."""

from typing import Annotated

from fastapi import Depends, FastAPI

from asyncticket.shared.domain.catalog import CatalogPolicy
from asyncticket.shared.infrastructure.catalog import (
    SqlAlchemyCatalogRelations, SqlAlchemyCatalogUnitOfWork,
)
from asyncticket.shows.application.service import ShowApplicationService
from asyncticket.shows.infrastructure.repositories import SqlAlchemyShowRepository
from asyncticket.wiring.common import DatabaseSession, get_catalog_policy


def provide_show_service() -> ShowApplicationService:
    raise NotImplementedError("ShowApplicationService 의존성이 주입되지 않았습니다.")


def create_show_service(
    session: DatabaseSession, policy: Annotated[CatalogPolicy, Depends(get_catalog_policy)],
) -> ShowApplicationService:
    return ShowApplicationService(
        SqlAlchemyShowRepository(session), SqlAlchemyCatalogRelations(session),
        SqlAlchemyCatalogUnitOfWork(session), policy,
    )


def wire_dependencies(app: FastAPI) -> None:
    app.dependency_overrides[provide_show_service] = create_show_service
