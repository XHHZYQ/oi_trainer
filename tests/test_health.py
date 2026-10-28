"""健康检查接口测试（不依赖真实 DB/Redis：DB 探活失败也返回 200）。"""
import os

# Settings 的必填项（fail-fast），测试环境直接注入进程环境变量
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/oi_trainer")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")

from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.main import app  # noqa: E402


async def test_health() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["db"] in ("up", "down")
