# app/models/schemas/requests.py
"""
Schemas Pydantic para requests da API.
Define estruturas de dados para validação de entrada.
"""
from pydantic import BaseModel, HttpUrl, validator, Field
from typing import Optional, List, Dict, Any
from datetime import date
from enum import Enum

class JobTypeEnum(str, Enum):
    """Enum para tipos de job."""
    OCR = "ocr"
    BARCODE = "barcode"
    QRCODE = "qrcode"
    ALL = "all"

class JobStatusEnum(str, Enum):
    """Enum para status de job."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

# ======================
# OCR REQUESTS
# ======================

class OCRProcessRequest(BaseModel):
    """Schema para processamento OCR via upload."""
    language: str = Field(default="pt", description="Idioma para reconhecimento")
    detect_orientation: bool = Field(default=True, description="Detectar orientação da imagem")
    return_confidence: bool = Field(default=False, description="Retornar scores de confiança")
    enhance_image: bool = Field(default=True, description="Aplicar melhorias na imagem")
    
    @validator('language')
    def validate_language(cls, v):
        supported = ['pt', 'en', 'es', 'fr', 'de', 'it']
        if v not in supported:
            raise ValueError(f'Idioma deve ser um de: {supported}')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "language": "pt",
                "detect_orientation": True,
                "return_confidence": True,
                "enhance_image": True
            }
        }

class OCRProcessURLRequest(BaseModel):
    """Schema para processamento OCR via URL."""
    image_url: HttpUrl = Field(description="URL da imagem para processamento")
    language: str = Field(default="pt", description="Idioma para reconhecimento")
    detect_orientation: bool = Field(default=True, description="Detectar orientação da imagem")
    return_confidence: bool = Field(default=False, description="Retornar scores de confiança")
    enhance_image: bool = Field(default=True, description="Aplicar melhorias na imagem")
    
    @validator('language')
    def validate_language(cls, v):
        supported = ['pt', 'en', 'es', 'fr', 'de', 'it']
        if v not in supported:
            raise ValueError(f'Idioma deve ser um de: {supported}')
        return v

# ======================
# BARCODE REQUESTS
# ======================

class BarcodeReadRequest(BaseModel):
    """Schema para leitura de códigos de barras."""
    barcode_types: Optional[List[str]] = Field(default=None, description="Tipos específicos de códigos")
    enhance_image: bool = Field(default=True, description="Aplicar melhorias na imagem")
    
    @validator('barcode_types')
    def validate_barcode_types(cls, v):
        if v is not None:
            valid_types = [
                'EAN13', 'EAN8', 'CODE128', 'CODE39', 'CODE93', 
                'CODABAR', 'ITF', 'QRCODE', 'PDF417', 'DATAMATRIX'
            ]
            for barcode_type in v:
                if barcode_type.upper() not in valid_types:
                    raise ValueError(f'Tipo de barcode inválido: {barcode_type}')
        return v

# ======================
# QRCODE REQUESTS
# ======================

class QRCodeReadRequest(BaseModel):
    """Schema para leitura de códigos QR."""
    multiple: bool = Field(default=False, description="Detectar múltiplos QR codes")
    enhance_image: bool = Field(default=True, description="Aplicar melhorias na imagem")

class QRCodeGenerateRequest(BaseModel):
    """Schema para geração de códigos QR."""
    data: str = Field(description="Dados para codificar no QR code", max_length=2000)
    size: int = Field(default=200, description="Tamanho da imagem em pixels", ge=50, le=1000)
    error_correction: str = Field(default="M", description="Nível de correção de erro")
    
    @validator('error_correction')
    def validate_error_correction(cls, v):
        valid_levels = ['L', 'M', 'Q', 'H']
        if v.upper() not in valid_levels:
            raise ValueError(f'Nível de correção deve ser um de: {valid_levels}')
        return v.upper()

# ======================
# COMBINED PROCESSING
# ======================

class ProcessAllRequest(BaseModel):
    """Schema para processamento combinado."""
    ocr_language: str = Field(default="pt", description="Idioma para OCR")
    include_ocr: bool = Field(default=True, description="Incluir processamento OCR")
    include_barcode: bool = Field(default=True, description="Incluir leitura de códigos de barras")
    include_qrcode: bool = Field(default=True, description="Incluir leitura de QR codes")
    enhance_image: bool = Field(default=True, description="Aplicar melhorias na imagem")
    
    @validator('ocr_language')
    def validate_language(cls, v):
        supported = ['pt', 'en', 'es', 'fr', 'de', 'it']
        if v not in supported:
            raise ValueError(f'Idioma deve ser um de: {supported}')
        return v

# ======================
# JOB MANAGEMENT
# ======================

class JobListRequest(BaseModel):
    """Schema para listagem de jobs."""
    page: int = Field(default=1, ge=1, description="Número da página")
    limit: int = Field(default=10, ge=1, le=100, description="Itens por página")
    job_type: Optional[JobTypeEnum] = Field(default=None, description="Filtrar por tipo de job")
    status: Optional[JobStatusEnum] = Field(default=None, description="Filtrar por status")
    date_from: Optional[date] = Field(default=None, description="Data inicial")
    date_to: Optional[date] = Field(default=None, description="Data final")
    order_by: str = Field(default="created_at", description="Campo para ordenação")
    order_dir: str = Field(default="desc", description="Direção da ordenação")
    search: Optional[str] = Field(default=None, description="Termo de busca")
    
    @validator('order_by')
    def validate_order_by(cls, v):
        valid_fields = ['created_at', 'completed_at', 'processing_time_ms', 'job_type', 'status']
        if v not in valid_fields:
            raise ValueError(f'order_by deve ser um de: {valid_fields}')
        return v
    
    @validator('order_dir')
    def validate_order_dir(cls, v):
        if v not in ['asc', 'desc']:
            raise ValueError('order_dir deve ser asc ou desc')
        return v

# ======================
# ANALYTICS REQUESTS
# ======================

class AnalyticsRequest(BaseModel):
    """Schema para requisições de analytics."""
    period_days: int = Field(default=7, ge=1, le=365, description="Período em dias")
    job_types: Optional[List[JobTypeEnum]] = Field(default=None, description="Tipos de job para filtrar")
    include_details: bool = Field(default=True, description="Incluir detalhes nas estatísticas")

class ReportRequest(BaseModel):
    """Schema para geração de relatórios customizados."""
    date_from: date = Field(description="Data inicial do relatório")
    date_to: date = Field(description="Data final do relatório")
    job_types: Optional[List[JobTypeEnum]] = Field(default=None, description="Tipos de job")
    group_by: str = Field(default="day", description="Agrupamento temporal")
    metrics: List[str] = Field(description="Métricas a incluir")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Filtros adicionais")
    format: str = Field(default="json", description="Formato do relatório")
    
    @validator('group_by')
    def validate_group_by(cls, v):
        valid_groups = ['hour', 'day', 'week', 'month']
        if v not in valid_groups:
            raise ValueError(f'group_by deve ser um de: {valid_groups}')
        return v
    
    @validator('metrics')
    def validate_metrics(cls, v):
        valid_metrics = [
            'count', 'avg_time', 'success_rate', 'total_size', 
            'avg_confidence', 'error_rate'
        ]
        for metric in v:
            if metric not in valid_metrics:
                raise ValueError(f'Métrica inválida: {metric}. Válidas: {valid_metrics}')
        return v
    
    @validator('format')
    def validate_format(cls, v):
        valid_formats = ['json', 'csv', 'xlsx']
        if v not in valid_formats:
            raise ValueError(f'Formato deve ser um de: {valid_formats}')
        return v

# ======================
# BATCH PROCESSING
# ======================

class BatchProcessRequest(BaseModel):
    """Schema para processamento em lote."""
    job_type: JobTypeEnum = Field(description="Tipo de processamento para todos os arquivos")
    processing_params: Optional[Dict[str, Any]] = Field(default=None, description="Parâmetros de processamento")
    max_files: int = Field(default=10, ge=1, le=50, description="Número máximo de arquivos")
    
class BatchStatusRequest(BaseModel):
    """Schema para consulta de status de lote."""
    batch_id: str = Field(description="ID do lote de processamento")

# ======================
# CONFIGURATION
# ======================

class ConfigUpdateRequest(BaseModel):
    """Schema para atualização de configurações."""
    rate_limit_per_minute: Optional[int] = Field(default=None, ge=1, le=1000)
    rate_limit_per_day: Optional[int] = Field(default=None, ge=1, le=10000)
    max_file_size_mb: Optional[int] = Field(default=None, ge=1, le=100)
    enable_analytics: Optional[bool] = Field(default=None)
    
# ======================
# USER SESSION
# ======================

class SessionUpdateRequest(BaseModel):
    """Schema para atualização de sessão."""
    preferred_language: Optional[str] = Field(default=None, description="Idioma preferido")
    timezone: Optional[str] = Field(default=None, description="Timezone do usuário")
    settings: Optional[Dict[str, Any]] = Field(default=None, description="Configurações personalizadas")