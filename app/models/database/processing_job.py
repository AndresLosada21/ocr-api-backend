# app/models/database/processing_job.py - VERSÃO ATUALIZADA COM RELATIONSHIPS
"""
Modelo principal para jobs de processamento.
Armazena informações sobre cada requisição de processamento (OCR, Barcode, QRCode).
"""
from sqlalchemy import Column, String, Integer, Text, Boolean, Float, JSON, DateTime
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import relationship
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import json

from app.models.database.base import BaseModel, JobType, JobStatus, JobTypeSQL, JobStatusSQL, LogMixin

class ProcessingJob(BaseModel, LogMixin):
    """
    Modelo principal para jobs de processamento.
    Centraliza todas as informações sobre uma requisição de processamento.
    """
    
    __tablename__ = "processing_jobs"
    __table_args__ = {
        'comment': 'Tabela principal para tracking de jobs de processamento'
    }
    
    # ======================
    # JOB IDENTIFICATION
    # ======================
    job_type = Column(
        JobTypeSQL,
        nullable=False,
        comment="Tipo de job: ocr, barcode, qrcode, all"
    )
    
    status = Column(
        JobStatusSQL,
        default=JobStatus.PENDING,
        nullable=False,
        comment="Status atual do job"
    )
    
    # ======================
    # INPUT METADATA
    # ======================
    input_filename = Column(
        String(255),
        nullable=True,
        comment="Nome original do arquivo enviado"
    )
    
    input_format = Column(
        String(10),
        nullable=True,
        comment="Formato do arquivo (jpg, png, pdf, etc.)"
    )
    
    input_size_bytes = Column(
        Integer,
        nullable=True,
        comment="Tamanho do arquivo em bytes"
    )
    
    input_dimensions = Column(
        JSON,
        nullable=True,
        comment="Dimensões da imagem: {width: int, height: int}"
    )
    
    input_hash = Column(
        String(64),
        nullable=True,
        comment="Hash SHA256 do arquivo para identificação única"
    )
    
    # ======================
    # PROCESSING PARAMETERS
    # ======================
    processing_params = Column(
        JSON,
        nullable=True,
        comment="Parâmetros específicos do processamento em JSON"
    )
    
    # ======================
    # RESULTS DATA
    # ======================
    results = Column(
        JSON,
        nullable=True,
        comment="Resultados completos do processamento em JSON"
    )
    
    results_summary = Column(
        Text,
        nullable=True,
        comment="Resumo textual dos resultados principais"
    )
    
    # ======================
    # ERROR HANDLING
    # ======================
    error_code = Column(
        String(50),
        nullable=True,
        comment="Código do erro se job falhou"
    )
    
    error_message = Column(
        Text,
        nullable=True,
        comment="Mensagem detalhada do erro"
    )
    
    error_details = Column(
        JSON,
        nullable=True,
        comment="Detalhes técnicos do erro em JSON"
    )
    
    # ======================
    # TIMING INFORMATION
    # ======================
    started_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data/hora de início do processamento"
    )
    
    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data/hora de conclusão do processamento"
    )
    
    processing_time_ms = Column(
        Integer,
        nullable=True,
        comment="Tempo total de processamento em milissegundos"
    )
    
    queue_time_ms = Column(
        Integer,
        nullable=True,
        comment="Tempo em fila antes do processamento"
    )
    
    # ======================
    # CLIENT INFORMATION
    # ======================
    client_ip = Column(
        INET,
        nullable=True,
        comment="Endereço IP do cliente"
    )
    
    user_agent = Column(
        Text,
        nullable=True,
        comment="User agent do cliente"
    )
    
    session_id = Column(
        String(128),
        nullable=True,
        comment="ID da sessão do usuário"
    )
    
    api_key = Column(
        String(64),
        nullable=True,
        comment="API key usada (se aplicável)"
    )
    
    # ======================
    # PERFORMANCE METRICS
    # ======================
    memory_usage_mb = Column(
        Float,
        nullable=True,
        comment="Uso máximo de memória durante processamento (MB)"
    )
    
    cpu_usage_percent = Column(
        Float,
        nullable=True,
        comment="Uso médio de CPU durante processamento (%)"
    )
    
    # ======================
    # QUALITY METRICS
    # ======================
    confidence_score = Column(
        Float,
        nullable=True,
        comment="Score de confiança médio dos resultados (0-1)"
    )
    
    quality_score = Column(
        Float,
        nullable=True,
        comment="Score de qualidade da imagem de entrada (0-1)"
    )
    
    # ======================
    # RELATIONSHIPS
    # ======================
    ocr_results = relationship(
        "OCRResult", 
        back_populates="job", 
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    barcode_results = relationship(
        "BarcodeResult", 
        back_populates="job", 
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    qrcode_results = relationship(
        "QRCodeResult", 
        back_populates="job", 
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    def __init__(self, **kwargs):
        """Inicializa um novo job de processamento."""
        super().__init__(**kwargs)
        if not self.status:
            self.status = JobStatus.PENDING
    
    def start_processing(self):
        """Marca o job como iniciado."""
        self.status = JobStatus.PROCESSING
        self.started_at = datetime.now(timezone.utc)
        if self.created_at:
            self.queue_time_ms = int((self.started_at - self.created_at).total_seconds() * 1000)
    
    def complete_successfully(self, results: Dict[str, Any], processing_time_ms: int):
        """Marca o job como concluído com sucesso."""
        self.status = JobStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        self.results = results
        self.processing_time_ms = processing_time_ms
        
        # Gerar resumo automático dos resultados
        self.results_summary = self._generate_results_summary(results)
    
    def fail_with_error(self, error_code: str, error_message: str, error_details: Dict[str, Any] = None):
        """Marca o job como falhou."""
        self.status = JobStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)
        self.error_code = error_code
        self.error_message = error_message
        self.error_details = error_details or {}
        
        if self.started_at:
            self.processing_time_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)
    
    def cancel(self, reason: str = None):
        """Cancela o job."""
        self.status = JobStatus.CANCELLED
        self.completed_at = datetime.now(timezone.utc)
        self.error_message = reason or "Job cancelado"
    
    def is_finished(self) -> bool:
        """Verifica se o job terminou (sucesso, falha ou cancelado)."""
        return self.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]
    
    def is_successful(self) -> bool:
        """Verifica se o job foi concluído com sucesso."""
        return self.status == JobStatus.COMPLETED
    
    def get_duration_seconds(self) -> Optional[float]:
        """Retorna a duração total em segundos."""
        if self.processing_time_ms:
            return self.processing_time_ms / 1000.0
        return None
    
    def set_performance_metrics(self, memory_mb: float = None, cpu_percent: float = None):
        """Define métricas de performance."""
        if memory_mb is not None:
            self.memory_usage_mb = memory_mb
        if cpu_percent is not None:
            self.cpu_usage_percent = cpu_percent
    
    def set_quality_metrics(self, confidence: float = None, quality: float = None):
        """Define métricas de qualidade."""
        if confidence is not None:
            self.confidence_score = max(0.0, min(1.0, confidence))
        if quality is not None:
            self.quality_score = max(0.0, min(1.0, quality))
    
    def update_processing_params(self, params: Dict[str, Any]):
        """Atualiza parâmetros de processamento."""
        if self.processing_params:
            self.processing_params.update(params)
        else:
            self.processing_params = params
    
    def add_debug_info(self, info: Dict[str, Any]):
        """Adiciona informações de debug."""
        debug_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "info": info
        }
        
        if self.debug_info:
            try:
                existing = json.loads(self.debug_info)
                if isinstance(existing, list):
                    existing.append(debug_data)
                else:
                    existing = [existing, debug_data]
            except (json.JSONDecodeError, TypeError):
                existing = [debug_data]
        else:
            existing = [debug_data]
        
        self.debug_info = json.dumps(existing)
    
    def get_detailed_results(self) -> Dict[str, Any]:
        """
        Retorna resultados detalhados incluindo relacionamentos.
        
        Returns:
            Dicionário com todos os resultados do job
        """
        detailed_results = {
            "job_info": self.to_dict(include_results=True, include_debug=False),
            "ocr_results": [result.to_dict() for result in self.ocr_results],
            "barcode_results": [result.to_dict() for result in self.barcode_results],
            "qrcode_results": [result.to_dict() for result in self.qrcode_results]
        }
        
        return detailed_results
    
    def get_results_count(self) -> Dict[str, int]:
        """
        Retorna contagem de resultados por tipo.
        
        Returns:
            Dicionário com contagens
        """
        return {
            "ocr_results": len(self.ocr_results),
            "barcode_results": len(self.barcode_results),
            "qrcode_results": len(self.qrcode_results),
            "total_results": len(self.ocr_results) + len(self.barcode_results) + len(self.qrcode_results)
        }
    
    def _generate_results_summary(self, results: Dict[str, Any]) -> str:
        """Gera um resumo textual dos resultados."""
        try:
            if self.job_type == JobType.OCR:
                return self._summarize_ocr_results(results)
            elif self.job_type == JobType.BARCODE:
                return self._summarize_barcode_results(results)
            elif self.job_type == JobType.QRCODE:
                return self._summarize_qrcode_results(results)
            elif self.job_type == JobType.ALL:
                return self._summarize_combined_results(results)
            else:
                return f"Processamento {self.job_type.value} concluído"
        except Exception:
            return "Resumo não disponível"
    
    def _summarize_ocr_results(self, results: Dict[str, Any]) -> str:
        """Resumo para resultados OCR."""
        text_blocks = results.get('text_blocks', [])
        full_text = results.get('full_text', '')
        language = results.get('language_detected', 'desconhecido')
        
        char_count = len(full_text)
        block_count = len(text_blocks)
        
        return f"OCR: {block_count} blocos, {char_count} caracteres, idioma: {language}"
    
    def _summarize_barcode_results(self, results: Dict[str, Any]) -> str:
        """Resumo para resultados de Barcode."""
        barcodes = results.get('barcodes', [])
        count = len(barcodes)
        
        if count == 0:
            return "Barcode: Nenhum código encontrado"
        elif count == 1:
            barcode_type = barcodes[0].get('type', 'desconhecido')
            return f"Barcode: 1 código {barcode_type} encontrado"
        else:
            types = [b.get('type', 'desconhecido') for b in barcodes]
            unique_types = list(set(types))
            return f"Barcode: {count} códigos encontrados ({', '.join(unique_types)})"
    
    def _summarize_qrcode_results(self, results: Dict[str, Any]) -> str:
        """Resumo para resultados de QR Code."""
        qr_codes = results.get('qr_codes', [])
        count = len(qr_codes)
        
        if count == 0:
            return "QR Code: Nenhum código encontrado"
        elif count == 1:
            data_type = qr_codes[0].get('data_type', 'texto')
            return f"QR Code: 1 código {data_type} encontrado"
        else:
            return f"QR Code: {count} códigos encontrados"
    
    def _summarize_combined_results(self, results: Dict[str, Any]) -> str:
        """Resumo para processamento combinado."""
        summaries = []
        
        if 'ocr' in results:
            ocr_summary = self._summarize_ocr_results(results['ocr'])
            summaries.append(ocr_summary)
        
        if 'barcodes' in results:
            barcode_summary = self._summarize_barcode_results(results['barcodes'])
            summaries.append(barcode_summary)
        
        if 'qr_codes' in results:
            qr_summary = self._summarize_qrcode_results(results['qr_codes'])
            summaries.append(qr_summary)
        
        return " | ".join(summaries) if summaries else "Processamento combinado concluído"
    
    def to_dict(self, include_results: bool = True, include_debug: bool = False, 
                include_relationships: bool = False) -> Dict[str, Any]:
        """
        Converte para dicionário com opções de inclusão.
        
        Args:
            include_results: Se deve incluir os resultados completos
            include_debug: Se deve incluir informações de debug
            include_relationships: Se deve incluir dados dos relacionamentos
        """
        exclude_fields = set()
        
        if not include_results:
            exclude_fields.update(['results', 'results_summary'])
        
        if not include_debug:
            exclude_fields.update(['debug_info', 'processing_notes'])
        
        data = super().to_dict(exclude_fields=exclude_fields)
        
        # Converter enums para strings
        if 'job_type' in data and data['job_type']:
            data['job_type'] = data['job_type'].value if hasattr(data['job_type'], 'value') else str(data['job_type'])
        
        if 'status' in data and data['status']:
            data['status'] = data['status'].value if hasattr(data['status'], 'value') else str(data['status'])
        
        # Incluir relacionamentos se solicitado
        if include_relationships:
            data['related_results'] = self.get_results_count()
            if include_results:
                data['ocr_details'] = [result.get_summary() for result in self.ocr_results]
                data['barcode_details'] = [result.get_summary() for result in self.barcode_results]
                data['qrcode_details'] = [result.get_summary() for result in self.qrcode_results]
        
        return data
    
    def __repr__(self) -> str:
        """Representação string do job."""
        return f"<ProcessingJob(id={self.id}, type={self.job_type}, status={self.status})>"

