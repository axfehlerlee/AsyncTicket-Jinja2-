# FastAPI 앱 생성 + 라우터 등록 (팀 공용)

# 함수를 "시작 → yield → 종료" 구조의 컨텍스트 매니저로 만들어 주는 데코레이터
from contextlib import asynccontextmanager
from fastapi import FastAPI
# engine: DB 연결(커넥션 풀) / close_db: 서버 종료 시 커넥션 풀 정리
from asyncticket.shared.core.database import close_db, engine
# 공용 로거 생성 함수
from asyncticket.shared.core.logger import get_logger
# Base : 모든 모델의 부모, 등록된 테이블 정보(metadata)를 가짐
# init_models : 모든 도메인 models.py를 import해서 Base에 테이블 등록
from asyncticket.shared.core.models import Base, init_models

# 이 파일에서 사용할 로거 (로그에 "app.main"이라는 이름으로 표시됨)
logger = get_logger("app.main")


# 서버 시작/종료 시 실행할 작업 정의
@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("애플리케이션 시작, 모델 초기화 및 DB 스키마 확인 중...")

    # 모든 models.py를 import → Base.metadata에 테이블 정보 등록
    init_models()

    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)

    logger.info("애플리케이션 준비 완료")
    # ───────── 여기서 멈춰서 서버가 요청을 처리 ─────────
    yield

    logger.info("애플리케이션 종료 처리 중...")
    await close_db()


# FastAPI 앱 생성 (uvicorn이 asyncticket.main:app으로 이 변수를 찾아 실행)
app = FastAPI(
    title="AsyncTicket API",
    description="공연 티켓 예매 백엔드 API",
    version="1.0.0",
    lifespan=lifespan,
)