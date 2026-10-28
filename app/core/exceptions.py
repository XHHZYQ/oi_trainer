"""业务异常与全局异常处理（统一输出信封格式）。"""
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


class BusinessException(Exception):
    """业务异常，默认 code=1。"""

    def __init__(self, msg: str = "业务错误", code: int = 1) -> None:
        self.msg = msg
        self.code = code
        super().__init__(msg)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BusinessException)
    async def business_exception_handler(request: Request, exc: BusinessException) -> JSONResponse:
        return JSONResponse({"code": exc.code, "data": None, "msg": exc.msg})

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            {"code": exc.status_code, "data": None, "msg": str(exc.detail)},
            status_code=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            {"code": 422, "data": jsonable_encoder(exc.errors()), "msg": "参数校验失败"},
            status_code=422,
        )

    @app.exception_handler(Exception)
    async def fallback_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse({"code": 500, "data": None, "msg": "服务器内部错误"}, status_code=500)
