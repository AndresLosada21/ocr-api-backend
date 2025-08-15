# app/api/routes/analytics.py
"""
Endpoints para análise e estatísticas da API.
Requer ENABLE_ANALYTICS=True nas settings.
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.crud.analytics import get_api_statistics, get_usage_by_type, get_error_stats
from app.models.schemas.analytics import AnalyticsSummary, UsageByType, ErrorStats
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    days: int = Query(7, ge=1, le=365, description="Período em dias"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Retorna resumo de analytics.
    """
    stats = get_api_statistics(db, days)
    logger.info(f"Analytics summary requested for {days} days")
    return stats

@router.get("/usage/by-type", response_model=UsageByType)
async def get_usage_by_job_type(
    days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Uso por tipo de job.
    """
    usage = get_usage_by_type(db, days)
    return usage

@router.get("/errors/stats", response_model=ErrorStats)
async def get_error_statistics(
    days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Estatísticas de erros.
    """
    errors = get_error_stats(db, days)
    return errors