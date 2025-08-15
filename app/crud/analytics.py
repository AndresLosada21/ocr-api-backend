# app/crud/analytics.py
"""
CRUD operations para analytics.
Usa queries SQLAlchemy para estatísticas.
"""
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone

from app.models.database.processing_job import ProcessingJob, JobType, JobStatus

def get_api_statistics(db: Session, days: int) -> Dict[str, Any]:
    """
    Obtém estatísticas gerais.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    query = db.query(ProcessingJob).filter(ProcessingJob.created_at >= cutoff)
    
    total_jobs = query.count()
    successful = query.filter(ProcessingJob.status == JobStatus.COMPLETED).count()
    failed = query.filter(ProcessingJob.status == JobStatus.FAILED).count()
    avg_time = query.with_entities(func.avg(ProcessingJob.processing_time_ms)).scalar() or 0
    
    return {
        "total_jobs": total_jobs,
        "successful": successful,
        "failed": failed,
        "success_rate": (successful / total_jobs * 100) if total_jobs else 0,
        "avg_processing_time_ms": avg_time
    }

def get_usage_by_type(db: Session, days: int) -> Dict[str, Any]:
    """
    Uso por tipo de job.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stats = db.query(
        ProcessingJob.job_type,
        func.count(ProcessingJob.id)
    ).filter(ProcessingJob.created_at >= cutoff).group_by(ProcessingJob.job_type).all()
    
    return {stat[0].value: stat[1] for stat in stats}

def get_error_stats(db: Session, days: int) -> Dict[str, Any]:
    """
    Estatísticas de erros.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    errors = db.query(
        ProcessingJob.error_code,
        func.count(ProcessingJob.id)
    ).filter(
        ProcessingJob.status == JobStatus.FAILED,
        ProcessingJob.created_at >= cutoff
    ).group_by(ProcessingJob.error_code).all()
    
    return {error[0]: error[1] for error in errors if error[0]}