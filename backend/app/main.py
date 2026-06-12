from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import (
    ai,
    backtests,
    dashboard,
    data_import,
    data_sources,
    etfs,
    industries,
    portfolios,
    projections,
)
from app.api.responses import APIError
from app.core.config import settings

app = FastAPI(title="ETF Portfolio Lab API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        code = detail.get("code")
        message = detail.get("message", str(detail))
    else:
        code = "HTTP_ERROR"
        message = str(detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": code, "message": message}},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "An internal error occurred."}},
    )


app.include_router(etfs.router, prefix="/api")
app.include_router(industries.router, prefix="/api")
app.include_router(portfolios.router, prefix="/api")
app.include_router(backtests.router, prefix="/api")
app.include_router(projections.router, prefix="/api")
app.include_router(data_sources.router, prefix="/api")
app.include_router(data_import.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Welcome to the ETF Portfolio Lab API"}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
