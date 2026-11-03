from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from asyncticket.shared.presentation.catalog_http import register_catalog_errors
from asyncticket.shared.domain.catalog import CatalogAuthenticator, CatalogPolicy

from asyncticket.performances.presentation.router import router as performance_router
from asyncticket.shared.core.database import close_db
from asyncticket.shows.presentation.router import router as show_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # 서버를 켠다는 이유로 DB 구조나 데이터를 바꾸지 않는다.
    try:
        yield
    finally:
        await close_db()


def create_app(
    authenticator: CatalogAuthenticator | None = None,
    policy: CatalogPolicy | None = None,
) -> FastAPI:
    app = FastAPI(title="AsyncTicket", lifespan=lifespan)
    # 앱 조립 지점에서만 공통 인증·정책과 두 도메인을 연결한다.
    app.state.catalog_authenticator = authenticator
    app.state.catalog_policy = policy if policy is not None else CatalogPolicy()
    register_catalog_errors(app)
    app.include_router(show_router)
    app.include_router(performance_router)
    return app


app = create_app()
