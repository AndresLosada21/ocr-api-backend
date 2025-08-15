# app/crud/processing_job.py
"""
Operações CRUD específicas para ProcessingJob.
Inclui funcionalidades avançadas de consulta e analytics.
"""
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from datetime import datetime, date, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func, text
from pydantic import BaseModel

from app.crud.base import CRUDBase
from app.models.database.processing_job import ProcessingJob, JobType, JobStatus
from app.models.database.ocr_result import OCRResult
from app.models.database.barcode_result import BarcodeResult
from app.models.database.qrcode_result import QRCodeResult

class ProcessingJobCreate(BaseModel):
    """Schema para criação de ProcessingJob."""
    job_type: str
    input_filename: Optional[str] = None
    input_format: Optional[str] = None
    input_size_bytes: Optional[int] = None
    input_dimensions: Optional[Dict[str, Any]] = None
    processing_params: Optional[Dict[str, Any]] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None

class ProcessingJobUpdate(BaseModel):
    """Schema para atualização de ProcessingJob."""
    status: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    processing_time_ms: Optional[int] = None

class CRUDProcessingJob(CRUDBase[ProcessingJob, ProcessingJobCreate, ProcessingJobUpdate]):
    """CRUD operations para ProcessingJob com funcionalidades especializadas."""
    
    def get_by_session(
        self, 
        db: Session, 
        session_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[ProcessingJob]:
        """
        Busca jobs por session_id.
        
        Args:
            db: Sessão do banco
            session_id: ID da sessão
            skip: Registros para pular
            limit: Limite de registros
            
        Returns:
            Lista de jobs da sessão
        """
        return db.query(ProcessingJob).filter(
            ProcessingJob.session_id == session_id
        ).order_by(desc(ProcessingJob.created_at)).offset(skip).limit(limit).all()
    
    def get_by_status(
        self, 
        db: Session, 
        status: JobStatus,
        skip: int = 0,
        limit: int = 100
    ) -> List[ProcessingJob]:
        """
        Busca jobs por status.
        
        Args:
            db: Sessão do banco
            status: Status do job
            skip: Registros para pular
            limit: Limite de registros
            
        Returns:
            Lista de jobs com o status especificado
        """
        return db.query(ProcessingJob).filter(
            ProcessingJob.status == status
        ).order_by(desc(ProcessingJob.created_at)).offset(skip).limit(limit).all()
    
    def get_by_type_and_period(
        self,
        db: Session,
        job_type: Optional[JobType] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ProcessingJob]:
        """
        Busca jobs por tipo e período.
        
        Args:
            db: Sessão do banco
            job_type: Tipo do job (opcional)
            date_from: Data inicial (opcional)
            date_to: Data final (opcional)
            skip: Registros para pular
            limit: Limite de registros
            
        Returns:
            Lista de jobs filtrados
        """
        query = db.query(ProcessingJob)
        
        if job_type:
            query = query.filter(ProcessingJob.job_type == job_type)
        
        if date_from:
            query = query.filter(ProcessingJob.created_at >= date_from)
        
        if date_to:
            query = query.filter(ProcessingJob.created_at <= date_to)
        
        return query.order_by(desc(ProcessingJob.created_at)).offset(skip).limit(limit).all()
    
    def get_pending_jobs(self, db: Session, limit: int = 10) -> List[ProcessingJob]:
        """
        Busca jobs pendentes para processamento.
        
        Args:
            db: Sessão do banco
            limit: Número máximo de jobs
            
        Returns:
            Lista de jobs pendentes ordenados por data de criação
        """
        return db.query(ProcessingJob).filter(
            ProcessingJob.status == JobStatus.PENDING
        ).order_by(asc(ProcessingJob.created_at)).limit(limit).all()
    
    def get_stuck_jobs(
        self, 
        db: Session, 
        timeout_minutes: int = 30
    ) -> List[ProcessingJob]:
        """
        Busca jobs que estão "presos" em processamento.
        
        Args:
            db: Sessão do banco
            timeout_minutes: Tempo limite em minutos
            
        Returns:
            Lista de jobs presos
        """
        timeout_time = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)
        
        return db.query(ProcessingJob).filter(
            and_(
                ProcessingJob.status == JobStatus.PROCESSING,
                ProcessingJob.started_at < timeout_time
            )
        ).all()
    
    def get_job_statistics(
        self, 
        db: Session, 
        period_days: int = 7
    ) -> Dict[str, Any]:
        """
        Retorna estatísticas detalhadas dos jobs.
        
        Args:
            db: Sessão do banco
            period_days: Período em dias para estatísticas
            
        Returns:
            Dicionário com estatísticas completas
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=period_days)
        
        # Estatísticas gerais
        base_query = db.query(ProcessingJob).filter(ProcessingJob.created_at >= cutoff_date)
        
        total_jobs = base_query.count()
        successful_jobs = base_query.filter(ProcessingJob.status == JobStatus.COMPLETED).count()
        failed_jobs = base_query.filter(ProcessingJob.status == JobStatus.FAILED).count()
        pending_jobs = base_query.filter(ProcessingJob.status == JobStatus.PENDING).count()
        processing_jobs = base_query.filter(ProcessingJob.status == JobStatus.PROCESSING).count()
        
        # Taxa de sucesso
        success_rate = (successful_jobs / total_jobs) if total_jobs > 0 else 0
        
        # Tempo médio de processamento
        avg_time = db.query(func.avg(ProcessingJob.processing_time_ms)).filter(
            and_(
                ProcessingJob.created_at >= cutoff_date,
                ProcessingJob.processing_time_ms.isnot(None)
            )
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
                "success_rate": round((stat.successful / stat.count) if stat.count > 0 else 0, 4)
            }
        
        # Estatísticas por dia
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
                "success_rate": round((stat.successful / stat.total) if stat.total > 0 else 0, 4),
                "avg_processing_time_ms": round(stat.avg_time or 0, 2)
            })
        
        # Top erros
        top_errors = db.query(
            ProcessingJob.error_code,
            func.count(ProcessingJob.id).label('count')
        ).filter(
            and_(
                ProcessingJob.created_at >= cutoff_date,
                ProcessingJob.status == JobStatus.FAILED,
                ProcessingJob.error_code.isnot(None)
            )
        ).group_by(ProcessingJob.error_code).order_by(desc(func.count(ProcessingJob.id))).limit(10).all()
        
        return {
            "period_days": period_days,
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
                "success_rate": round(success_rate, 4),
                "avg_processing_time_ms": round(avg_time, 2)
            },
            "by_job_type": by_job_type,
            "daily_stats": daily_data,
            "top_errors": [
                {"error_code": error.error_code, "count": error.count} 
                for error in top_errors
            ]
        }
    
    def get_performance_metrics(
        self, 
        db: Session, 
        period_days: int = 7
    ) -> Dict[str, Any]:
        """
        Retorna métricas de performance detalhadas.
        
        Args:
            db: Sessão do banco
            period_days: Período em dias
            
        Returns:
            Métricas de performance
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=period_days)
        
        # Query para jobs completados no período
        completed_jobs = db.query(ProcessingJob).filter(
            and_(
                ProcessingJob.created_at >= cutoff_date,
                ProcessingJob.status == JobStatus.COMPLETED,
                ProcessingJob.processing_time_ms.isnot(None)
            )
        )
        
        # Percentis de tempo de processamento
        processing_times = [job.processing_time_ms for job in completed_jobs.all()]
        
        if processing_times:
            processing_times.sort()
            n = len(processing_times)
            
            percentiles = {
                "p50": processing_times[int(n * 0.5)],
                "p75": processing_times[int(n * 0.75)],
                "p90": processing_times[int(n * 0.9)],
                "p95": processing_times[int(n * 0.95)],
                "p99": processing_times[int(n * 0.99)] if n > 100 else processing_times[-1]
            }
        else:
            percentiles = {"p50": 0, "p75": 0, "p90": 0, "p95": 0, "p99": 0}
        
        # Throughput (jobs por hora)
        total_hours = period_days * 24
        throughput = len(processing_times) / total_hours if total_hours > 0 else 0
        
        # Tamanho médio de arquivos
        avg_file_size = db.query(func.avg(ProcessingJob.input_size_bytes)).filter(
            and_(
                ProcessingJob.created_at >= cutoff_date,
                ProcessingJob.input_size_bytes.isnot(None)
            )
        ).scalar() or 0
        
        return {
            "period_days": period_days,
            "completed_jobs_count": len(processing_times),
            "processing_time_percentiles": percentiles,
            "throughput_jobs_per_hour": round(throughput, 2),
            "avg_file_size_bytes": round(avg_file_size, 2),
            "avg_file_size_mb": round(avg_file_size / (1024 * 1024), 2) if avg_file_size > 0 else 0
        }
    
    def get_client_statistics(
        self, 
        db: Session, 
        period_days: int = 7
    ) -> Dict[str, Any]:
        """
        Retorna estatísticas de clientes/sessões.
        
        Args:
            db: Sessão do banco
            period_days: Período em dias
            
        Returns:
            Estatísticas de clientes
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=period_days)
        
        # Sessões únicas
        unique_sessions = db.query(func.count(func.distinct(ProcessingJob.session_id))).filter(
            and_(
                ProcessingJob.created_at >= cutoff_date,
                ProcessingJob.session_id.isnot(None)
            )
        ).scalar() or 0
        
        # IPs únicos
        unique_ips = db.query(func.count(func.distinct(ProcessingJob.client_ip))).filter(
            and_(
                ProcessingJob.created_at >= cutoff_date,
                ProcessingJob.client_ip.isnot(None)
            )
        ).scalar() or 0
        
        # Top sessões por número de jobs
        top_sessions = db.query(
            ProcessingJob.session_id,
            func.count(ProcessingJob.id).label('job_count')
        ).filter(
            and_(
                ProcessingJob.created_at >= cutoff_date,
                ProcessingJob.session_id.isnot(None)
            )
        ).group_by(ProcessingJob.session_id).order_by(desc(func.count(ProcessingJob.id))).limit(10).all()
        
        return {
            "period_days": period_days,
            "unique_sessions": unique_sessions,
            "unique_ips": unique_ips,
            "top_sessions": [
                {"session_id": session.session_id, "job_count": session.job_count}
                for session in top_sessions
            ]
        }
    
    def cleanup_old_jobs(
        self, 
        db: Session, 
        retention_days: int = 90,
        batch_size: int = 1000
    ) -> int:
        """
        Remove jobs antigos baseado na política de retenção.
        
        Args:
            db: Sessão do banco
            retention_days: Dias de retenção
            batch_size: Tamanho do lote para remoção
            
        Returns:
            Número de jobs removidos
        """