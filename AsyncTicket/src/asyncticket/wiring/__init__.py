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
# [이 파일: 공용 연결 진입점]
# 앱 생성 코드에서 wire_dependencies(app)를 호출하면 여기서 도메인별 등록 함수를 부른다.
# 좌석 인프라·표현 계층은 비워둔 상태다. 공연·회차·공연장·결제 등록은 유지한다.
# 등록은 app.dependency_overrides에 대체 함수 관계를 넣는 작업이며, 그 자체로 DB 조회는 하지 않는다.
# 공연·회차 라우터는 provide_* 계약을 Depends로 사용하고, wiring이 실제 생성 함수를 연결한다.
# 개별 좌석 연결은 해당 서비스·저장소를 함께 작성한 뒤 추가한다.

"""도메인별 의존성 연결의 공용 진입점."""
from fastapi import FastAPI
from asyncticket.wiring.catalog_auth import wire_dependencies as wire_catalog_auth_dependencies
from asyncticket.wiring.shows import wire_dependencies as wire_show_dependencies
from asyncticket.wiring.performances import wire_dependencies as wire_performance_dependencies
from asyncticket.wiring.venues import wire_dependencies as wire_venue_dependencies
from asyncticket.wiring.payment import wire_dependencies as wire_payment_dependencies

def wire_dependencies(app: FastAPI) -> None:
    wire_catalog_auth_dependencies(app)
    wire_show_dependencies(app)
    wire_performance_dependencies(app)
    wire_venue_dependencies(app)
    wire_payment_dependencies(app)
