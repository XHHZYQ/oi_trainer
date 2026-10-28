"""统一响应信封 {code, data, msg}。"""
import json
from typing import Any

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute


def ok(data: Any = None, msg: str = "ok") -> dict[str, Any]:
    """成功响应信封。"""
    return {"code": 0, "data": data, "msg": msg}


class EnvelopeRoute(APIRoute):
    """把路由返回值统一包装为 {code, data, msg}；已带 code 的响应原样返回。"""

    def get_route_handler(self):
        original_handler = super().get_route_handler()

        async def custom_handler(request: Request) -> Response:
            response = await original_handler(request)
            if not hasattr(response, "body"):
                return response
            if not response.headers.get("content-type", "").startswith("application/json"):
                return response
            body = json.loads(response.body)
            if isinstance(body, dict) and "code" in body:
                return response
            return JSONResponse({"code": 0, "data": body, "msg": "ok"}, status_code=response.status_code)

        return custom_handler
