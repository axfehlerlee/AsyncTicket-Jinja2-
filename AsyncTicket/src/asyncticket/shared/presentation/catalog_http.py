"""표현 계층: 도메인 예외를 API 명세의 HTTP 오류 응답으로 변환한다."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from asyncticket.shared.domain.catalog import (
    AuthenticationRequiredError, CatalogConflictError, CatalogForbiddenError,
    CatalogIntegrationError, CatalogNotFoundError, CatalogValidationError,
)

ERRORS = {
    AuthenticationRequiredError: (401, "AUTHENTICATION_REQUIRED"),
    CatalogForbiddenError: (403, "PERMISSION_DENIED"),
    CatalogNotFoundError: (404, "RESOURCE_NOT_FOUND"),
    CatalogConflictError: (409, "RESOURCE_CONFLICT"),
    CatalogValidationError: (422, "VALIDATION_ERROR"),
    CatalogIntegrationError: (503, "INTEGRATION_UNAVAILABLE"),
}


def register_catalog_errors(app: FastAPI) -> None:
    async def domain_error(request: Request, exc: Exception) -> JSONResponse:
        status, code = next(value for kind, value in ERRORS.items() if isinstance(exc, kind))
        headers = {"WWW-Authenticate": "Bearer"} if status == 401 else None
        return JSONResponse(
            status_code=status, content={"detail": {"code": code, "message": str(exc)}},
            headers=headers,
        )

    async def invalid_input(request: Request, exc: RequestValidationError) -> JSONResponse:
        # 입력 원문과 내부 예외를 노출하지 않고 명세의 공통 형식으로 변환한다.
        return JSONResponse(status_code=422, content={"detail": {
            "code": "VALIDATION_ERROR", "message": "요청 입력값을 확인해 주세요."
        }})

    for error in ERRORS:
        app.add_exception_handler(error, domain_error)
    app.add_exception_handler(RequestValidationError, invalid_input)
