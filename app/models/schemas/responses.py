# app/models/schemas/responses.py
"""
Schemas Pydantic para responses da API.
Define estruturas de dados para respostas padronizadas.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from uuid import UUID

# ======================
# BASE RESPONSES
# ======================

class BaseResponse(BaseModel):
    """Schema base para todas as respostas."""
    success: bool = Field(description="Indica se a operação foi bem-sucedida")
    timestamp: datetime = Field(description="Timestamp da resposta")

class SuccessResponse(BaseResponse):
    """Schema para respostas de sucesso."""
    success: bool = True
    data: Any = Field(description="Dados da resposta")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Metadados adicionais")

class ErrorResponse(BaseResponse):
    """Schema para respostas de erro."""
    success: bool = False
    error: Dict[str, Any] = Field(description="Informações do erro")

class ErrorDetail(BaseModel):
    """Schema para detalhes de erro."""
    code: str = Field(description="Código do erro")
    message: str = Field(description="Mensagem do erro")
    details: Optional[Any] = Field(default=None, description="Detalhes adicionais do erro")

# ======================
# HEALTH CHECK RESPONSES
# ======================

class ServiceStatus(BaseModel):
    """Schema para status de um serviço."""
    status: str = Field(description="Status do serviço")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Detalhes do serviço")

class SystemInfo(BaseModel):
    """Schema para informações do sistema."""
    cpu_usage: float = Field(description="Uso de CPU em percentual")
    memory_usage: float = Field(description="Uso de memória em percentual")
    disk_usage: float = Field(description="Uso de disco em percentual")
    uptime_seconds: float = Field(description="Tempo de atividade em segundos")
    process_id: int = Field(description="ID do processo")

class HealthResponse(BaseModel):
    """Schema para resposta de health check."""
    status: str = Field(description="Status geral da aplicação")
    timestamp: datetime = Field(description="Timestamp da verificação")
    version: str = Field(description="Versão da API")
    environment: str = Field(description="Ambiente (dev, prod, etc.)")
    response_time_ms: float = Field(description="Tempo de resposta em ms")
    services: Dict[str, ServiceStatus] = Field(description="Status dos serviços")
    system: SystemInfo = Field(description="Informações do sistema")

# ======================
# JOB RESPONSES
# ======================

class TextBlock(BaseModel):
    """Schema para bloco de texto do OCR."""
    text: str = Field(description="Texto extraído")
    bbox: List[List[float]] = Field(description="Coordenadas da bounding box")
    confidence: Optional[float] = Field(default=None, description="Confiança da detecção")

class BarcodeData(BaseModel):
    """Schema para dados de código de barras."""
    data: str = Field(description="Dados decodificados")
    type: str = Field(description="Tipo do código")
    bbox: List[List[float]] = Field(description="Coordenadas da bounding box")
    quality: str = Field(description="Qualidade da leitura")
    checksum_valid: bool = Field(description="Se o checksum é válido")

class QRCodeData(BaseModel):
    """Schema para dados de código QR."""
    data: str = Field(description="Dados decodificados")
    data_type: str = Field(description="Tipo de dados (url, text, etc.)")
    bbox: List[List[float]] = Field(description="Coordenadas da bounding box")
    error_correction_level: str = Field(description="Nível de correção de erro")
    version: int = Field(description="Versão do QR code")

class JobMetadata(BaseModel):
    """Schema para metadados de um job."""
    input_image: Dict[str, Any] = Field(description="Informações da imagem de entrada")
    processing_params: Dict[str, Any] = Field(description="Parâmetros de processamento")
    model_info: Optional[Dict[str, Any]] = Field(default=None, description="Informações do modelo usado")

# ======================
# OCR RESPONSES
# ======================

class OCRResponse(BaseModel):
    """Schema para resposta de processamento OCR."""
    job_id: UUID = Field(description="ID único do job")
    job_type: str = Field(default="ocr", description="Tipo do job")
    status: str = Field(description="Status do processamento")
    text_blocks: List[TextBlock] = Field(description="Blocos de texto encontrados")
    full_text: str = Field(description="Texto completo extraído")
    language_detected: str = Field(description="Idioma detectado")
    processing_time_ms: int = Field(description="Tempo de processamento em ms")
    created_at: datetime = Field(description="Data/hora de criação")

class OCRProcessResponse(SuccessResponse):
    """Schema para resposta completa de processamento OCR."""
    data: OCRResponse
    metadata: JobMetadata

# ======================
# BARCODE RESPONSES
# ======================

class BarcodeResponse(BaseModel):
    """Schema para resposta de leitura de códigos de barras."""
    job_id: UUID = Field(description="ID único do job")
    job_type: str = Field(default="barcode", description="Tipo do job")
    status: str = Field(description="Status do processamento")
    barcodes: List[BarcodeData] = Field(description="Códigos de barras encontrados")
    count: int = Field(description="Número de códigos encontrados")
    processing_time_ms: int = Field(description="Tempo de processamento em ms")
    created_at: datetime = Field(description="Data/hora de criação")

class BarcodeReadResponse(SuccessResponse):
    """Schema para resposta completa de leitura de códigos de barras."""
    data: BarcodeResponse
    metadata: JobMetadata

# ======================
# QRCODE RESPONSES
# ======================

class QRCodeResponse(BaseModel):
    """Schema para resposta de leitura de códigos QR."""
    job_id: UUID = Field(description="ID único do job")
    job_type: str = Field(default="qrcode", description="Tipo do job")
    status: str = Field(description="Status do processamento")
    qr_codes: List[QRCodeData] = Field(description="Códigos QR encontrados")
    count: int = Field(description="Número de códigos encontrados")
    processing_time_ms: int = Field(description="Tempo de processamento em ms")
    created_at: datetime = Field(description="Data/hora de criação")

class QRCodeReadResponse(SuccessResponse):
    """Schema para resposta completa de leitura de códigos QR."""
    data: QRCodeResponse
    metadata: JobMetadata

class QRCodeGenerateData(BaseModel):
    """Schema para dados de QR code gerado."""
    data: str = Field(description="Dados codificados")
    data_type: str = Field(description="Tipo de dados")
    image_base64: str = Field(description="Imagem do QR code em base64")
    size: int = Field(description="Tamanho da imagem")
    error_correction: str = Field(description="Nível de correção usado")
    format: str = Field(description="Formato da imagem")

class QRCodeGenerateResponse(BaseModel):
    """Schema para resposta de geração de QR code."""
    job_id: UUID = Field(description="ID único do job")
    job_type: str = Field(default="qrcode_generation", description="Tipo do job")
    status: str = Field(description="Status do processamento")
    qr_code: QRCodeGenerateData = Field(description="QR code gerado")
    processing_time_ms: int = Field(description="Tempo de processamento em ms")
    created_at: datetime = Field(description="Data/hora de criação")

# ======================
# COMBINED PROCESSING
# ======================

class ProcessAllResults(BaseModel):
    """Schema para resultados de processamento combinado."""
    ocr: Optional[Dict[str, Any]] = Field(default=None, description="Resultados OCR")
    barcodes: Optional[Dict[str, Any]] = Field(default=None, description="Resultados de códigos de barras")
    qr_codes: Optional[Dict[str, Any]] = Field(default=None, description="Resultados de códigos QR")

class ProcessAllResponse(BaseModel):
    """Schema para resposta de processamento combinado."""
    job_id: UUID = Field(description="ID único do job")
    job_type: str = Field(default="all", description="Tipo do job")
    status: str = Field(description="Status do processamento")
    results: ProcessAllResults = Field(description="Resultados de todos os tipos")
    processing_time_ms: int = Field(description="Tempo total de processamento em ms")
    created_at: datetime = Field(description="Data/hora de criação")

# ======================
# JOB MANAGEMENT
# ======================

class JobSummary(BaseModel):
    """Schema para resumo de um job."""
    job_id: UUID = Field(description="ID único do job")
    job_type: str = Field(description="Tipo do job")
    status: str = Field(description="Status atual")
    created_at: datetime = Field(description="Data/hora de criação")
    completed_at: Optional[datetime] = Field(default=None, description="Data/hora de conclusão")
    processing_time_ms: Optional[int] = Field(default=None, description="Tempo de processamento")
    input_filename: Optional[str] = Field(default=None, description="Nome do arquivo")
    input_size_bytes: Optional[int] = Field(default=None, description="Tamanho do arquivo")
    success: bool = Field(description="Se foi bem-sucedido")
    error_code: Optional[str] = Field(default=None, description="Código de erro se falhou")
    results_summary: Optional[str] = Field(default=None, description="Resumo dos resultados")

class JobDetail(BaseModel):
    """Schema para detalhes completos de um job."""
    job_id: UUID = Field(description="ID único do job")
    job_type: str = Field(description="Tipo do job")
    status: str = Field(description="Status atual")
    created_at: datetime = Field(description="Data/hora de criação")
    started_at: Optional[datetime] = Field(default=None, description="Data/hora de início")
    completed_at: Optional[datetime] = Field(default=None, description="Data/hora de conclusão")
    processing_time_ms: Optional[int] = Field(default=None, description="Tempo de processamento")
    queue_time_ms: Optional[int] = Field(default=None, description="Tempo em fila")
    input_metadata: Dict[str, Any] = Field(description="Metadados da entrada")
    processing_params: Dict[str, Any] = Field(description="Parâmetros de processamento")
    results: Optional[Dict[str, Any]] = Field(default=None, description="Resultados completos")
    error_info: Optional[Dict[str, Any]] = Field(default=None, description="Informações de erro")
    performance_metrics: Optional[Dict[str, Any]] = Field(default=None, description="Métricas de performance")
    client_info: Dict[str, Any] = Field(description="Informações do cliente")

class PaginationInfo(BaseModel):
    """Schema para informações de paginação."""
    page: int = Field(description="Página atual")
    limit: int = Field(description="Itens por página")
    total: int = Field(description="Total de itens")
    total_pages: int = Field(description="Total de páginas")
    has_next: bool = Field(description="Se há próxima página")
    has_prev: bool = Field(description="Se há página anterior")

class JobListResponse(SuccessResponse):
    """Schema para resposta de listagem de jobs."""
    data: Dict[str, Any] = Field(description="Dados da listagem")

class JobListData(BaseModel):
    """Schema para dados de listagem de jobs."""
    jobs: List[JobSummary] = Field(description="Lista de jobs")
    pagination: PaginationInfo = Field(description="Informações de paginação")
    filters_applied: Dict[str, Any] = Field(description="Filtros aplicados")

# ======================
# ANALYTICS RESPONSES
# ======================

class StatisticsSummary(BaseModel):
    """Schema para resumo de estatísticas."""
    total_jobs: int = Field(description="Total de jobs")
    successful_jobs: int = Field(description="Jobs bem-sucedidos")
    failed_jobs: int = Field(description="Jobs falhados")
    pending_jobs: int = Field(description="Jobs pendentes")
    processing_jobs: int = Field(description="Jobs em processamento")
    success_rate: float = Field(description="Taxa de sucesso")
    avg_processing_time_ms: float = Field(description="Tempo médio de processamento")

class JobTypeStats(BaseModel):
    """Schema para estatísticas por tipo de job."""
    count: int = Field(description="Número de jobs")
    avg_processing_time_ms: float = Field(description="Tempo médio de processamento")
    success_rate: float = Field(description="Taxa de sucesso")

class DailyStat(BaseModel):
    """Schema para estatística diária."""
    date: str = Field(description="Data no formato ISO")
    total_jobs: int = Field(description="Total de jobs no dia")
    successful_jobs: int = Field(description="Jobs bem-sucedidos")
    success_rate: float = Field(description="Taxa de sucesso")
    avg_processing_time_ms: float = Field(description="Tempo médio de processamento")

class PerformanceMetrics(BaseModel):
    """Schema para métricas de performance."""
    p50_processing_time_ms: float = Field(description="Percentil 50 do tempo de processamento")
    p90_processing_time_ms: float = Field(description="Percentil 90 do tempo de processamento")
    p95_processing_time_ms: float = Field(description="Percentil 95 do tempo de processamento")
    p99_processing_time_ms: float = Field(description="Percentil 99 do tempo de processamento")

class AnalyticsData(BaseModel):
    """Schema para dados de analytics."""
    period_days: int = Field(description="Período analisado em dias")
    date_range: Dict[str, str] = Field(description="Intervalo de datas")
    summary: StatisticsSummary = Field(description="Resumo das estatísticas")
    by_job_type: Dict[str, JobTypeStats] = Field(description="Estatísticas por tipo")
    daily_stats: List[DailyStat] = Field(description="Estatísticas diárias")
    performance_metrics: PerformanceMetrics = Field(description="Métricas de performance")

class AnalyticsResponse(SuccessResponse):
    """Schema para resposta de analytics."""
    data: AnalyticsData

# ======================
# BATCH RESPONSES
# ======================

class BatchJobResult(BaseModel):
    """Schema para resultado de um job em lote."""
    job_id: Optional[UUID] = Field(default=None, description="ID do job")
    filename: str = Field(description="Nome do arquivo")
    status: str = Field(description="Status do processamento")
    results: Optional[Dict[str, Any]] = Field(default=None, description="Resultados se bem-sucedido")
    error: Optional[str] = Field(default=None, description="Erro se falhou")

class BatchResponse(BaseModel):
    """Schema para resposta de processamento em lote."""
    batch_id: UUID = Field(description="ID único do lote")
    total_files: int = Field(description="Total de arquivos processados")
    successful_files: int = Field(description="Arquivos processados com sucesso")
    failed_files: int = Field(description="Arquivos que falharam")
    processing_time_ms: int = Field(description="Tempo total de processamento")
    results: List[BatchJobResult] = Field(description="Resultados individuais")

# ======================
# CONFIGURATION RESPONSES
# ======================

class ConfigurationData(BaseModel):
    """Schema para dados de configuração."""
    api_version: str = Field(description="Versão da API")
    supported_formats: List[str] = Field(description="Formatos suportados")
    max_file_size_mb: int = Field(description="Tamanho máximo de arquivo")
    max_concurrent_jobs: int = Field(description="Jobs simultâneos máximos")
    features: Dict[str, bool] = Field(description="Features habilitadas")
    limits: Dict[str, Any] = Field(description="Limites da API")

class ConfigurationResponse(SuccessResponse):
    """Schema para resposta de configuração."""
    data: ConfigurationData

# ======================
# LIST RESPONSES
# ======================

class LanguageInfo(BaseModel):
    """Schema para informações de idioma."""
    code: str = Field(description="Código do idioma")
    name: str = Field(description="Nome do idioma")
    supported: bool = Field(description="Se é suportado")

class FormatInfo(BaseModel):
    """Schema para informações de formato."""
    extension: str = Field(description="Extensão do arquivo")
    mime_type: str = Field(description="Tipo MIME")
    description: str = Field(description="Descrição do formato")

class SupportedLanguagesResponse(SuccessResponse):
    """Schema para resposta de idiomas suportados."""
    data: Dict[str, Any]

class SupportedFormatsResponse(SuccessResponse):
    """Schema para resposta de formatos suportados."""
    data: Dict[str, Any]