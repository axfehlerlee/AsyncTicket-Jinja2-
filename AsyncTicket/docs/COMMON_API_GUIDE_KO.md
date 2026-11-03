# AsyncTicket 공통 모듈 — 튜터 원문 기준

2026-11-04 사용자가 제공한 수업 자료로 교체했다.
DB 연결(database.py)·로거(logger.py)는 교체하지 않았다.

## 파일과 적용

- shared/core/schemas.py: 튜터 APIResponse 원문. 성공은 ok(data=...), 실패는 fail(...).
- shared/core/exceptions.py: 튜터 SharedException 및 400/401/403/404/409/422 예외 원문.
- shared/core/exception_handlers.py: 튜터 업무 예외·요청 검증 오류·미처리 오류 처리기 원문.
- 공통 ORM 모델과 DateTimeBase는 이 PR 범위에 포함하지 않는다.
- container.py: 튜터의 공용 wire_dependencies 진입점에 기존 좌석 DI 연결을 보존.
- main.py: 이 PR에서는 수정하지 않는다. 기존 공연·회차 처리기는 그대로 유지한다.

튜터 자료의 shared.core import는 asyncticket.shared.core로 변경했다.
쇼핑몰 이름·user 단독 모델 등록은 팀A 이름과 실제 모델 등록으로 맞췄다.
pyproject.toml의 package=false는 넣지 않았다. 팀A는 src/asyncticket 패키지를
유지하며 실제 uv 실행에 사용한다. 추가 인증 라이브러리도 이 교체로 설치하지 않았다.

## 팀원 적용

성공: 자기 DTO를 APIResponse[자기DTO].ok(data=...)로 반환하고 라우터의
response_model도 APIResponse[자기DTO]로 맞춘다. 201과 Location은 유지하며
본문 없는 204는 감싸지 않는다. 성공 자동 래핑은 없다.

실패: 공통 예외를 직접 사용하거나 상속한다.

```python
from asyncticket.shared.core.exceptions import NotFoundException

# 각 담당자의 서비스에서 적용할 예시
# raise NotFoundException("공연을 찾을 수 없습니다.", error_code="SHOW_NOT_FOUND")
```

Catalog 전용 예외 변환표는 없다. 각 담당자가 자기 예외·응답·명세·테스트를
공통 형식으로 전환한다. 다른 담당자 코드는 이번 교체에서 수정하지 않았다.
향후 앱 조립에서 register_catalog_errors를 register_exception_handlers로 전환해야 한다.
따라서 전환하지 않은 Catalog 예외는 기존 4xx 의미를 자동 유지하지 못하고
미처리 500으로 처리될 수 있다. 팀 전체 적용 완료로 간주하지 않는다.

## 튜터 원문 그대로인 동작과 한계

- errors는 Any를 포함하며, 공통 예외 파일은 fastapi.status를 사용한다.
- HTTPException과 프레임워크의 없는 경로 404는 FastAPI 기본 처리를 유지한다.
  모든 HTTP 오류가 APIResponse로 감싸지는 것은 아니다.
- SharedException 401에는 별도 WWW-Authenticate 헤더 추가 기능이 없다.
- 미처리 예외는 logger.exception으로 기록하고 일반 500 메시지로 응답한다.
- DateTimeBase는 포함하지 않았으며 팀 모델·테이블·컬럼 변경도 없다.

## 검사

```sh
uv run --with httpx python -B -m unittest discover -s tests/shared_core -v
```

별도 FastAPI 앱에서 성공·업무 상태·422·기본 HTTPException/404·500 마스킹을
검사한다. 실제 DB·JWT·전체 팀 도메인의 통합 성공을 증명하지 않는다.


## 관련 작업

좌석 API의 공통 응답 적용은 후속 PR에서 제공한다. 이 PR은 공통 모듈의 독립 검사만 포함한다.


## DB 세션 종료 시 저장 확정

get_db는 yield 이후 정상적으로 돌아오면 commit하고, 요청 처리 또는 commit에서
예외가 발생하면 rollback한 뒤 예외를 다시 전달한다. 연결 설정·풀 옵션은 유지한다.
기존 서비스가 먼저 commit한 내용까지 나중 rollback으로 취소할 수 있는 것은 아니다.
요청 전체의 원자성과 저장 확정 책임을 통일하는 작업은 별도 통합 검토가 필요하다.
의존성 정리 시점과 실제 HTTP 응답 전송 시점도 별도이며, 이 단위 검사는 HTTP 전송
이전에 commit이 끝나는 것을 보장하지 않는다.
