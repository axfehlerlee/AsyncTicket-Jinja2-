# 좌석 도메인 4계층·공통 응답 적용

공통 API 모듈 PR을 선행 기반으로 사용한다. 공통 API 처리기는 팀 main.py에 자동 등록하지 않는다.
실제 앱 조립 담당자는 공통 처리기 등록과 seats.container.wire_dependencies(app),
seats.presentation.router.router 등록을 함께 수행해야 한다. 기존 Catalog 오류의 전환도 별도다.

## 포함 기능

- SeatInfo의 설정·수량 검사와 저장소 ABC
- SQLAlchemy 저장소의 회차별 목록·좌석 단건 조회, 도메인 객체 변환
- 목록/단건 GET을 APIResponse.data에 반환, 404/422/500 공통 오류 선언
- 내부 예매 연결 함수의 조건부 UPDATE 및 409/422 예외
- 예매 전 좌석의 reserv_id NULL 허용 (ORM 변경)

공개 API는 GET /v1/performances/{perf_id}/seats 및
GET /v1/performances/{perf_id}/seats/{seat_seq}다.
안쪽 응답은 기존 SeatListResponse/SeatResponse이며 success/code 등의 공통 필드는 바깥에 둔다.

## 검증·남은 작업

좌석 조회/연결 15개와 도메인 12개를 독립 앱·메모리 SQLite에서 검사한다.
실제 PostgreSQL·JWT·팀 전체 ORM 초기화·부하 검증은 수행하지 않았다.
회차/예매 테이블의 최소 테스트 픽스처는 테스트 전용이다.

기존 PostgreSQL 테이블의 NOT NULL은 ORM 변경만으로 갱신되지 않는다.
실제 마이그레이션/ERD 반영은 별도이며 이 PR에서 DB를 변경하지 않는다.
seat_seq 유일성, 좌석 상태값, 생성 시점, 취소 이력 계약은 팀 후속 확인이 필요하다.
좌석 생성 API·본인 예매 좌석 조회·예매 API 전체는 구현 범위에 포함하지 않는다.
조회는 선점하거나 예매 상태를 변경하지 않는다.
