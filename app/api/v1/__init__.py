"""v1 路由聚合：统一挂在 /api/v1 前缀下。"""
from fastapi import APIRouter

from app.api.v1 import accounts, auth, classes, courses, knowledge_points

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(accounts.router)
api_router.include_router(courses.router)
api_router.include_router(classes.router)
api_router.include_router(knowledge_points.router)
