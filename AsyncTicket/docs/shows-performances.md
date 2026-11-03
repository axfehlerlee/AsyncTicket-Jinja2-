# 공연·공연회차 API 명세 대응

공연 5개와 공연회차 5개, 총 10개 API를 구현한다.
[4계층과 코드 흐름 설명](four-layer-guide.md)을 먼저 읽으면 각 파일의 역할을 확인할 수 있다.

## 명세와 코드 대응표

| 기능 | Method | Path | 성공 | 라우터 → 서비스 |
| --- | --- | --- | --- | --- |
| 공연 목록 | GET | `/v1/shows` | 200 | `get_list_show` → `find_all` |
| 공연 상세 | GET | `/v1/shows/{show_id}` | 200 | `get_detail_show` → `find_by_id` |
| 공연 등록 | POST | `/v1/shows` | 201 + Location | `create_show` → `create` |
| 공연 수정 | PATCH | `/v1/shows/{show_id}` | 200 | `update_show` → `update` |
| 공연 삭제 | DELETE | `/v1/shows/{show_id}` | 204, 본문 없음 | `delete_show` → `delete` |
| 공연별 회차 목록 | GET | `/v1/shows/{show_id}/performances` | 200 | `get_list_performance` → `find_all` |
| 회차 상세 | GET | `/v1/performances/{perf_id}` | 200 | `get_detail_performance` → `find_by_id` |
| 회차 등록 | POST | `/v1/shows/{show_id}/performances` | 201 + Location | `create_performance` → `create` |
| 회차 수정 | PATCH | `/v1/performances/{perf_id}` | 200 | `update_performance` → `update` |
| 회차 삭제 | DELETE | `/v1/performances/{perf_id}` | 204, 본문 없음 | `delete_performance` → `delete` |

- 공연 목록은 `page=1`, `size=20`(1~100), `keyword`, `type`, `venues_id`를 받는다.
  `{items, page, size, total}`을 반환한다. 검색어의 %와 _는 실제 문자로 검색한다.
- 회차 목록은 선택 `date=YYYY-MM-DD`를 받는다. 한국 날짜의 자정 이상~다음 자정 미만을
  조회하고 `{items}`를 반환한다. 숫자·날짜+시간 문자열은 422다.
  허용 범위는 `0001-01-02`~`9999-12-30`이다. KST 자정의 UTC 변환이 Python의
  최소 연도 아래로 넘어가는 `0001-01-01`은 422로 거절하며 기존 상한도 유지한다.
- 공연 응답은 명세의 9개 공개 필드를 반환하고 `user_id`를 제외한다.
  회차 응답은 `perf_id`부터 `status`까지 명세의 9개 필드를 반환한다.
- 공연 등록은 명세의 공연장·제목·소개·출연자·분류·시간을 받는다.
  ID·소유자·등록/수정시각은 본문에서 받지 않는다.
- 회차 등록은 URL의 공연 소속을 사용하고 명세의 시간·회차번호·매수·상태를 받는다.
  매수 생략 기본값은 3이다. status는 필수이며 예시 SCHEDULED를 Enum으로 고정하지 않는다.
- 생성 Location은 각각 `/v1/shows/{show_id}`, `/v1/performances/{perf_id}`다.
- PATCH는 최소 1개 필드, 미지정 값 유지, nullable 값의 null 허용, 불변/알 수 없는 필드 거절이다.
- 없는 대상은 404, 잘못된 입력은 422, 변경 권한 없음은 403, 연결/중복 충돌은 409다.
  오류 형식은 명세 예시에 맞춘 `{detail: {code, message}}`다.

## 명세의 제안·미정 사항에 적용한 값

아래는 구현 선택을 명시한 것으로 팀 최종 합의 또는 운영 검증을 의미하지 않는다.

| 항목 | 현재 구현 |
| --- | --- |
| 소유권 | SELLER는 본인 공연만, ADMIN은 전체 관리. `CatalogPolicy`에서 관리 |
| 공연 분류·회차 상태 | 비어 있지 않은 길이 제한 문자열. 최종 허용값이 정해지면 policy allowlist로 설정 |
| 공연 시간·회차번호·매수 | 양수, 매수 기본 3. 최근 회의의 1매 방향을 임의로 적용하지 않음 |
| 시간순서 | 예매 시작 < 예매 마감 ≤ 공연 시작 < 공연 종료, 시간대 필수 |
| 공연 내 회차번호 | 부모 공연 잠금 후 중복 조회, 중복 409. 새 DB UNIQUE 제약을 추가하지 않음 |
| 공연장 변경 | 연결 회차가 있으면 409 |
| 회차 상태 변경 | 좌석 구성/예매가 연결돼 있어도 상태만 변경하는 PATCH 허용. 인증·소유권·상태 허용값 검사 유지 |
| 회차 일정·회차번호·매수 변경 | 연결 좌석 구성/예매가 있으면 실제 값 변경 409. 상태 변경과 섞은 PATCH도 전체 거절. policy로 관리 |
| 삭제 | 공연은 연결 회차 없음, 회차는 연결 좌석정보·예매 없음일 때만 물리 삭제 |
| 좌석 생성·환불 | 이 두 API 영역에서 자동 수행하지 않음. 명세의 별도 처리 경계를 유지 |

예를 들어 좌석 생성 뒤 `PATCH /v1/performances/{perf_id}`에 `{"status": "ON_SALE"}`을
보내면 상태를 변경할 수 있다. `ON_SALE`은 흐름 설명용 예시이며 최종 상태 허용값과
전이 규칙은 팀 합의 후 `CatalogPolicy`에 연결한다. 상태 변경이 예매 취소·환불을
자동 실행하지는 않는다. 삭제 및 연결 데이터 변경 제한은 그대로 적용한다.

공연 목록은 등록시각·ID 내림차순, 회차 목록은 시작시각·ID 오름차순이다.
트랜잭션의 commit/rollback은 응용 서비스에서 결정하며 변경 실패는 되돌린다.
부모 공연 잠금은 이 기능의 회차 변경을 조율하지만, 다른 도메인이 같은 잠금 규약을
사용하는지 및 실제 PostgreSQL 동시성은 별도 검증 대상이다.

## 공통 인증 연결

팀 공통 인증 모듈이 검증한 사용자 ID·역할을 사용해야 한다.
앱을 조립할 때 `create_app(authenticator=팀인증어댑터)`로 연결한다.
어댑터의 비동기 `authenticate(token)`은 검증에 성공하면
`CatalogActor(user_id, role)`, 실패하면 `None`을 반환한다.

토큰 없음/검증 실패는 `401 + WWW-Authenticate: Bearer`다.
공통 인증 미연결 상태에서 Bearer 토큰을 보내면 503으로 중단한다.
테스트용 토큰·임의 사용자 헤더를 운영 인증으로 제공하지 않는다.

## 실행·검증

프로젝트 폴더에서 다음 명령을 실행한다.

```powershell
uv sync --frozen
uv run python -m unittest discover -s tests -v
uv run uvicorn asyncticket.main:app --host 127.0.0.1 --port 8000
```

`/docs`에 10개 작업이 표시된다. 실제 데이터 요청에는 PostgreSQL의 명세 테이블과
공통 인증 연결이 필요하다. DB 설정은 기존 `shared/core/database.py`의 환경 변수 규칙을 따른다.
서버 기동 시 테이블 생성·삭제·시드 입력을 자동 실행하지 않는다.

테스트는 격리 SQLite에서 실제 저장소 SQL을 실행하고, ASGI 요청으로 10개 API의
정상·권한·검증·충돌·삭제·롤백·Location·응답 필드를 확인한다.
SQLite 테스트 어댑터의 시간대·PK 처리는 PostgreSQL과의 차이를 시험 환경에서만 보정한다.
PostgreSQL DDL 컴파일 검사는 실제 DB 적용·동시성·부하 검증이 아니다.

## 팀 통합 시 남은 사항

- dev에 공통 인증 구현이 아직 없어 인증 어댑터 연결이 필요하다.
- 팀 dev에 병합된 공연장 모델의 PK는 `id`인데 명세/공연 FK는 `venues_id`다.
  dev와 이 브랜치를 통합할 때 공연장 담당과 이름을 맞춰야 한다.
- 기존 예매 모델의 `from sqlalchemy import Decimal` 오류로 전체 `init_models()`가 실패한다.
  예매 담당 파일은 변경하지 않았다.
- 공연장 PK/FK를 맞춘 전체 메타데이터 DDL 통합 검증이 필요하다. 연결 조회용 Core 컬럼
  선언은 실제 테이블 조회 계약이며 대체 ORM 모델 또는 테이블 생성 코드가 아니다.
- 의존성/lockfile·타 담당 도메인 모델·DB 데이터는 변경하지 않았다.
