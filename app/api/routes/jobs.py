# app/api/routes/jobs.py
"""
Endpoints para gestão e consulta de jobs de processamento.
Permite consultar histórico, status e detalhes de jobs.
"""
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime, date, timezone, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func
from pydantic import BaseModel, validator

from app.config.database import get_db
from app.config.settings import settings
from app.models.database.processing_job import ProcessingJob, JobType, JobStatus
from app.utils.exceptions import JobNotFound, ValidationError
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Schemas para responses
class JobSummary(BaseModel):
    """Resumo de job para listagens."""
    job_id: str
    job_type: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    processing_time_ms: Optional[int]
    input_filename: Optional[str]
    input_size_bytes: Optional[int]
    success: bool
    error_code: Optional[str]

class JobDetail(BaseModel):
    """Detalhes completos de um job."""
    job_id: str
    job_type: str
    status: str
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    processing_time_ms: Optional[int]
    queue_time_ms: Optional[int]
    input_metadata: Dict[str, Any]
    processing_params: Dict[str, Any]
    results: Optional[Dict[str, Any]]
    error_info: Optional[Dict[str, Any]]
    performance_metrics: Optional[Dict[str, Any]]

class JobListQuery(BaseModel):
    """Parâmetros de consulta para lista de jobs."""
    page: int = 1
    limit: int = 10
    job_type: Optional[str] = None
    status: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    order_by: str = "created_at"
    order_dir: str = "desc"
    
    @validator('limit')
    def validate_limit(cls, v):
        if v < 1 or v > 100:
            raise ValueError('Limit deve estar entre 1 e 100')
        return v
    
    @validator('page')
    def validate_page(cls, v):
        if v < 1:
            raise ValueError('Page deve ser maior que 0')
        return v
    
    @validator('job_type')
    def validate_job_type(cls, v):
        if v and v not in ['ocr', 'barcode', 'qrcode', 'all']:
            raise ValueError('job_type deve ser: ocr, barcode, qrcode ou all')
        return v
    
    @validator('status')
    def validate_status(cls, v):
        if v and v not in ['pending', 'processing', 'completed', 'failed', 'cancelled']:
            raise ValueError('status deve ser: pending, processing, completed, failed ou cancelled')
        return v
    
    @validator('order_by')
    def validate_order_by(cls, v):
        allowed = ['created_at', 'completed_at', 'processing_time_ms', 'job_type', 'status']
        if v not in allowed:
            raise ValueError(f'order_by deve ser um de: {allowed}')
        return v
    
    @validator('order_dir')
    def validate_order_dir(cls, v):
        if v not in ['asc', 'desc']:
            raise ValueError('order_dir deve ser asc ou desc')
        return v

@router.get("/jobs/{job_id}", tags=["Jobs"])
async def get_job_by_id(
    job_id: UUID,
    include_results: bool = Query(True, description="Incluir resultados completos"),
    include_debug: bool = Query(False, description="Incluir informações de debug"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Consulta detalhes de um job específico por ID.
    
    Args:
        job_id: ID único do job
        include_results: Se deve incluir resultados completos
        include_debug: Se deve incluir informações de debug
        db: Sessão do banco de dados
        
    Returns:
        Detalhes completos do job
    """
    try:
        # Buscar job no banco
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        
        if not job:
            raise JobNotFound(str(job_id))
        
        logger.info(
            f"Consultando job {job_id}",
            extra={
                "job_id": str(job_id),
                "include_results": include_results,
                "include_debug": include_debug
            }
        )
        
        # Preparar metadados de input
        input_metadata = {
            "filename": job.input_filename,
            "size_bytes": job.input_size_bytes,
            "format": job.input_format,
            "dimensions": job.input_dimensions,
            "hash": job.input_hash
        }
        
        # Preparar informações de erro
        error_info = None
        if job.status == JobStatus.FAILED:
            error_info = {
                "error_code": job.error_code,
                "error_message": job.error_message,
                "error_details": job.error_details
            }
        
        # Preparar métricas de performance
        performance_metrics = {}
        if job.processing_time_ms:
            performance_metrics["processing_time_ms"] = job.processing_time_ms
        if job.queue_time_ms:
            performance_metrics["queue_time_ms"] = job.queue_time_ms
        if job.memory_usage_mb:
            performance_metrics["memory_usage_mb"] = job.memory_usage_mb
        if job.cpu_usage_percent:
            performance_metrics["cpu_usage_percent"] = job.cpu_usage_percent
        if job.confidence_score:
            performance_metrics["confidence_score"] = job.confidence_score
        if job.quality_score:
            performance_metrics["quality_score"] = job.quality_score
        
        # Montar resposta
        job_data = {
            "job_id": str(job.id),
            "job_type": job.job_type.value,
            "status": job.status.value,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "processing_time_ms": job.processing_time_ms,
            "queue_time_ms": job.queue_time_ms,
            "input_metadata": input_metadata,
            "processing_params": job.processing_params or {},
            "results_summary": job.results_summary,
            "error_info": error_info,
            "performance_metrics": performance_metrics if performance_metrics else None,
            "client_info": {
                "ip_address": str(job.client_ip) if job.client_ip else None,
                "user_agent": job.user_agent,
                "session_id": job.session_id,
                "api_key": job.api_key
            }
        }
        
        # Incluir resultados completos se solicitado
        if include_results and job.results:
            job_data["results"] = job.results
        
        # Incluir debug se solicitado
        if include_debug:
            job_data["debug_info"] = job.debug_info
            job_data["processing_notes"] = job.processing_notes
        
        return {
            "success": True,
            "data": job_data
        }
        
    except JobNotFound:
        raise
    except Exception as e:
        logger.error(f"Erro ao consultar job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/jobs", tags=["Jobs"])
async def list_jobs(
    page: int = Query(1, ge=1, description="Número da página"),
    limit: int = Query(10, ge=1, le=100, description="Itens por página"),
    job_type: Optional[str] = Query(None, description="Filtrar por tipo de job"),
    status: Optional[str] = Query(None, description="Filtrar por status"),
    date_from: Optional[date] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="Data final (YYYY-MM-DD)"),
    order_by: str = Query("created_at", description="Campo para ordenação"),
    order_dir: str = Query("desc", description="Direção da ordenação"),
    search: Optional[str] = Query(None, description="Buscar por nome de arquivo"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Lista jobs com filtros e paginação.
    
    Args:
        page: Número da página
        limit: Quantidade de itens por página
        job_type: Filtro por tipo (ocr, barcode, qrcode, all)
        status: Filtro por status
        date_from: Data inicial para filtro
        date_to: Data final para filtro
        order_by: Campo para ordenação
        order_dir: Direção da ordenação (asc/desc)
        search: Termo de busca para nome de arquivo
        db: Sessão do banco de dados
        
    Returns:
        Lista paginada de jobs
    """
    try:
        # Validar parâmetros usando o schema
        query_params = JobListQuery(
            page=page,
            limit=limit,
            job_type=job_type,
            status=status,
            date_from=date_from,
            date_to=date_to,
            order_by=order_by,
            order_dir=order_dir
        )
        
        # Construir query base
        query = db.query(ProcessingJob)
        
        # Aplicar filtros
        filters = []
        
        if query_params.job_type:
            filters.append(ProcessingJob.job_type == JobType(query_params.job_type))
        
        if query_params.status:
            filters.append(ProcessingJob.status == JobStatus(query_params.status))
        
        if query_params.date_from:
            filters.append(ProcessingJob.created_at >= datetime.combine(query_params.date_from, datetime.min.time()))
        
        if query_params.date_to:
            filters.append(ProcessingJob.created_at <= datetime.combine(query_params.date_to, datetime.max.time()))
        
        if search:
            filters.append(ProcessingJob.input_filename.ilike(f"%{search}%"))
        
        if filters:
            query = query.filter(and_(*filters))
        
        # Contar total de registros
        total_count = query.count()
        
        # Aplicar ordenação
        order_column = getattr(ProcessingJob, query_params.order_by)
        if query_params.order_dir == "desc":
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(asc(order_column))
        
        # Aplicar paginação
        offset = (query_params.page - 1) * query_params.limit
        jobs = query.offset(offset).limit(query_params.limit).all()
        
        # Preparar resultados
        job_summaries = []
        for job in jobs:
            job_summaries.append({
                "job_id": str(job.id),
                "job_type": job.job_type.value,
                "status": job.status.value,
                "created_at": job.created_at.isoformat(),
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "processing_time_ms": job.processing_time_ms,
                "input_filename": job.input_filename,
                "input_size_bytes": job.input_size_bytes,
                "success": job.status == JobStatus.COMPLETED,
                "error_code": job.error_code,
                "results_summary": job.results_summary
            })
        
        # Calcular informações de paginação
        total_pages = (total_count + query_params.limit - 1) // query_params.limit
        has_next = query_params.page < total_pages
        has_prev = query_params.page > 1
        
        logger.info(
            f"Listando jobs",
            extra={
                "page": query_params.page,
                "limit": query_params.limit,
                "total_count": total_count,
                "filters_applied": len(filters)
            }
        )
        
        return {
            "success": True,
            "data": {
                "jobs": job_summaries,
                "pagination": {
                    "page": query_params.page,
                    "limit": query_params.limit,
                    "total": total_count,
                    "total_pages": total_pages,
                    "has_next": has_next,
                    "has_prev": has_prev
                },
                "filters_applied": {
                    "job_type": query_params.job_type,
                    "status": query_params.status,
                    "date_range": f"{query_params.date_from} to {query_params.date_to}" if query_params.date_from or query_params.date_to else None,
                    "search": search
                }
            }
        }
        
    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Erro ao listar jobs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/jobs/stats", tags=["Jobs"])
async def get_jobs_statistics(
    days: int = Query(7, ge=1, le=90, description="Período em dias para estatísticas"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Retorna estatísticas gerais dos jobs.
    
    Args:
        days: Período em dias para calcular estatísticas
        db: Sessão do banco de dados
        
    Returns:
        Estatísticas dos jobs no período
    """
    try:
        # Data de corte
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Query base
        base_query = db.query(ProcessingJob).filter(ProcessingJob.created_at >= cutoff_date)
        
        # Estatísticas gerais
        total_jobs = base_query.count()
        successful_jobs = base_query.filter(ProcessingJob.status == JobStatus.COMPLETED).count()
        failed_jobs = base_query.filter(ProcessingJob.status == JobStatus.FAILED).count()
        pending_jobs = base_query.filter(ProcessingJob.status == JobStatus.PENDING).count()
        processing_jobs = base_query.filter(ProcessingJob.status == JobStatus.PROCESSING).count()
        
        # Taxa de sucesso
        success_rate = (successful_jobs / total_jobs * 100) if total_jobs > 0 else 0
        
        # Tempo médio de processamento
        avg_processing_time = db.query(func.avg(ProcessingJob.processing_time_ms)).filter(
            ProcessingJob.created_at >= cutoff_date,
            ProcessingJob.processing_time_ms.isnot(None)
        ).scalar() or 0
        
        # Estatísticas por tipo de job
        job_type_stats = db.query(
            ProcessingJob.job_type,
            func.count(ProcessingJob.id).label('count'),
            func.avg(ProcessingJob.processing_time_ms).label('avg_time'),
            func.count(ProcessingJob.id).filter(ProcessingJob.status == JobStatus.COMPLETED).label('successful')
        ).filter(
            ProcessingJob.created_at >= cutoff_date
        ).group_by(ProcessingJob.job_type).all()
        
        by_job_type = {}
        for stat in job_type_stats:
            by_job_type[stat.job_type.value] = {
                "count": stat.count,
                "avg_processing_time_ms": round(stat.avg_time or 0, 2),
                "success_rate": round((stat.successful / stat.count * 100) if stat.count > 0 else 0, 2)
            }
        
        # Estatísticas por dia (últimos 7 dias)
        daily_stats = db.query(
            func.date(ProcessingJob.created_at).label('date'),
            func.count(ProcessingJob.id).label('total'),
            func.count(ProcessingJob.id).filter(ProcessingJob.status == JobStatus.COMPLETED).label('successful'),
            func.avg(ProcessingJob.processing_time_ms).label('avg_time')
        ).filter(
            ProcessingJob.created_at >= cutoff_date
        ).group_by(func.date(ProcessingJob.created_at)).order_by(func.date(ProcessingJob.created_at)).all()
        
        daily_data = []
        for stat in daily_stats:
            daily_data.append({
                "date": stat.date.isoformat(),
                "total_jobs": stat.total,
                "successful_jobs": stat.successful,
                "success_rate": round((stat.successful / stat.total * 100) if stat.total > 0 else 0, 2),
                "avg_processing_time_ms": round(stat.avg_time or 0, 2)
            })
        
        return {
            "success": True,
            "data": {
                "period_days": days,
                "date_range": {
                    "from": cutoff_date.isoformat(),
                    "to": datetime.now(timezone.utc).isoformat()
                },
                "summary": {
                    "total_jobs": total_jobs,
                    "successful_jobs": successful_jobs,
                    "failed_jobs": failed_jobs,
                    "pending_jobs": pending_jobs,
                    "processing_jobs": processing_jobs,
                    "success_rate": round(success_rate, 2),
                    "avg_processing_time_ms": round(avg_processing_time, 2)
                },
                "by_job_type": by_job_type,
                "daily_stats": daily_data
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.delete("/jobs/{job_id}", tags=["Jobs"])
async def cancel_job(
    job_id: UUID,
    reason: Optional[str] = Query(None, description="Motivo do cancelamento"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Cancela um job em andamento.
    
    Args:
        job_id: ID do job a ser cancelado
        reason: Motivo do cancelamento
        db: Sessão do banco de dados
        
    Returns:
        Confirmação do cancelamento
    """
    try:
        # Buscar job
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        
        if not job:
            raise JobNotFound(str(job_id))
        
        # Verificar se pode ser cancelado
        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            raise ValidationError(f"Job já foi finalizado com status: {job.status.value}")
        
        # Cancelar job
        job.cancel(reason or "Cancelado pelo usuário")
        db.commit()
        
        logger.info(
            f"Job cancelado",
            extra={
                "job_id": str(job_id),
                "reason": reason,
                "previous_status": job.status.value
            }
        )
        
        return {
            "success": True,
            "data": {
                "job_id": str(job_id),
                "status": "cancelled",
                "reason": reason or "Cancelado pelo usuário",
                "cancelled_at": job.completed_at.isoformat()
            }
        }
        
    except (JobNotFound, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Erro ao cancelar job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

# Import necessário para timedelta
from datetime import timedelta