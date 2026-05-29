"""健康检查路由。"""
from fastapi import APIRouter

from ..database import check_db_connection

router = APIRouter()


@router.get("/health")
async def health_check():
    """服务健康检查。"""
    db_ok = await check_db_connection()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "version": "2.0.0",
    }
