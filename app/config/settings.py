"""
Configurações da aplicação OCR API Backend.
Centraliza todas as variáveis de ambiente e configurações.
"""
from pydantic import validator
from pydantic_settings import BaseSettings
from typing import List, Optional
import os
from pathlib import Path

class Settings(BaseSettings):
    """Configurações principais da aplicação."""
    
    # ======================
    # SERVER CONFIGURATION
    # ======================
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    DEBUG: bool = False
    ENV: str = "production"
    API_VERSION: str = "v1"
    API_PREFIX: str = "/api/v1"
    
    # ======================
    # DATABASE CONFIGURATION
    # ======================
    DATABASE_URL: str = "postgresql://postgres:postgres123@postgres:5432/ocr_api"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600
    DATABASE_ECHO: bool = False  # Para desenvolvimento, logs SQL
    
    # ======================
    # OCR CONFIGURATION
    # ======================
    PADDLE_OCR_USE_GPU: bool = False
    PADDLE_OCR_LANG: str = "pt"
    PADDLE_OCR_USE_ANGLE_CLS: bool = True
    PADDLE_OCR_USE_SPACE_CHAR: bool = True
    OCR_MODEL_DIR: str = "/app/models/paddle_ocr"
    PADDLE_OCR_DET: bool = True
    PADDLE_OCR_REC: bool = True
    PADDLE_OCR_CLS: bool = True
    
    # ======================
    # FILE PROCESSING
    # ======================
    MAX_IMAGE_SIZE_MB: int = 10
    MAX_REQUEST_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: str = "jpg,jpeg,png,pdf,bmp,tiff"
    TEMP_UPLOAD_DIR: str = "/tmp/ocr_uploads"
    CLEANUP_TEMP_FILES: bool = True
    IMAGE_QUALITY_ENHANCEMENT: bool = True
    MAX_IMAGE_DIMENSION: int = 4096  # pixels
    MIN_IMAGE_DIMENSION: int = 32    # pixels
    
    # ======================
    # SECURITY
    # ======================
    CORS_ORIGINS: str = "*"
    CORS_METHODS: str = "GET,POST,PUT,DELETE,OPTIONS"
    CORS_HEADERS: str = "*"
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    RATE_LIMIT_REQUESTS_PER_DAY: int = 1000
    SESSION_SECRET_KEY: str = "your-super-secret-key-change-in-production"
    API_KEY_HEADER: str = "X-API-Key"
    
    # ======================
    # LOGGING
    # ======================
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json ou text
    LOG_FILE_PATH: Optional[str] = "/app/logs/ocr_api.log"
    LOG_ROTATION_SIZE: str = "100MB"
    LOG_RETENTION_DAYS: int = 30
    LOG_REQUEST_BODY: bool = False  # Log request bodies (cuidado com imagens)
    
    # ======================
    # ANALYTICS
    # ======================
    ENABLE_ANALYTICS: bool = True
    ANALYTICS_RETENTION_DAYS: int = 90
    ENABLE_PERFORMANCE_METRICS: bool = True
    ENABLE_CLIENT_TRACKING: bool = True
    ENABLE_GEOLOCATION: bool = False
    
    # ======================
    # MONITORING
    # ======================
    ENABLE_HEALTH_CHECKS: bool = True
    HEALTH_CHECK_INTERVAL: int = 30
    ENABLE_PROMETHEUS_METRICS: bool = False
    PROMETHEUS_PORT: int = 9090
    
    # ======================
    # PERFORMANCE
    # ======================
    WORKER_PROCESSES: int = 1
    WORKER_CONNECTIONS: int = 1000
    KEEPALIVE_TIMEOUT: int = 75
    MAX_CONCURRENT_JOBS: int = 10
    JOB_TIMEOUT_SECONDS: int = 300
    ENABLE_GZIP: bool = True
    
    # ======================
    # FEATURES FLAGS
    # ======================
    ENABLE_OCR: bool = True
    ENABLE_BARCODE: bool = True
    ENABLE_QRCODE: bool = True
    ENABLE_BATCH_PROCESSING: bool = False
    ENABLE_WEBHOOKS: bool = False
    
    @validator('ALLOWED_EXTENSIONS')
    def validate_extensions(cls, v):
        """Valida e normaliza extensões de arquivo permitidas."""
        if isinstance(v, str):
            return [ext.strip().lower() for ext in v.split(',')]
        return v
    
    @validator('CORS_ORIGINS')
    def validate_cors_origins(cls, v):
        """Valida origens CORS."""
        if v == "*":
            return ["*"]
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    @validator('CORS_METHODS')
    def validate_cors_methods(cls, v):
        """Valida métodos CORS."""
        if isinstance(v, str):
            return [method.strip() for method in v.split(',')]
        return v
    
    @validator('CORS_HEADERS')
    def validate_cors_headers(cls, v):
        """Valida headers CORS."""
        if v == "*":
            return ["*"]
        if isinstance(v, str):
            return [header.strip() for header in v.split(',')]
        return v
    
    @validator('LOG_LEVEL')
    def validate_log_level(cls, v):
        """Valida nível de log."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'LOG_LEVEL deve ser um de: {valid_levels}')
        return v.upper()
    
    @validator('ENV')
    def validate_environment(cls, v):
        """Valida ambiente."""
        valid_envs = ['development', 'testing', 'staging', 'production']
        if v.lower() not in valid_envs:
            raise ValueError(f'ENV deve ser um de: {valid_envs}')
        return v.lower()
    
    @property
    def max_image_size_bytes(self) -> int:
        """Tamanho máximo de imagem em bytes."""
        return self.MAX_IMAGE_SIZE_MB * 1024 * 1024
    
    @property
    def max_request_size_bytes(self) -> int:
        """Tamanho máximo de request em bytes."""
        return self.MAX_REQUEST_SIZE_MB * 1024 * 1024
    
    @property
    def is_development(self) -> bool:
        """Verifica se está em ambiente de desenvolvimento."""
        return self.ENV == "development" or self.DEBUG
    
    @property
    def is_production(self) -> bool:
        """Verifica se está em ambiente de produção."""
        return self.ENV == "production"
    
    @property
    def database_url_sync(self) -> str:
        """URL do banco para operações síncronas."""
        return self.DATABASE_URL.replace("postgresql://", "postgresql://")
    
    @property
    def database_url_async(self) -> str:
        """URL do banco para operações assíncronas."""
        return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    
    def get_cors_config(self) -> dict:
        """Retorna configuração CORS."""
        return {
            "allow_origins": self.CORS_ORIGINS,
            "allow_methods": self.CORS_METHODS,
            "allow_headers": self.CORS_HEADERS,
            "allow_credentials": True
        }
    
    def create_temp_dir(self) -> Path:
        """Cria diretório temporário se não existir."""
        temp_path = Path(self.TEMP_UPLOAD_DIR)
        temp_path.mkdir(parents=True, exist_ok=True)
        return temp_path
    
    def create_log_dir(self) -> Optional[Path]:
        """Cria diretório de logs se especificado."""
        if self.LOG_FILE_PATH:
            log_path = Path(self.LOG_FILE_PATH).parent
            log_path.mkdir(parents=True, exist_ok=True)
            return log_path
        return None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        validate_assignment = True

# Instância global das configurações
settings = Settings()

# Validações adicionais na inicialização
def validate_settings():
    """Validações adicionais das configurações."""
    
    # Criar diretórios necessários
    settings.create_temp_dir()
    settings.create_log_dir()
    
    # Validar configurações críticas
    if settings.is_production and settings.SESSION_SECRET_KEY == "ysour-super-secret-key-change-in-production":
        raise ValueError("SESSION_SECRET_KEY deve ser alterada em produção!")
    
    if settings.MAX_IMAGE_SIZE_MB > 100:
        raise ValueError("MAX_IMAGE_SIZE_MB muito alto (máximo recomendado: 100MB)")
    
    if settings.MAX_CONCURRENT_JOBS > 50:
        raise ValueError("MAX_CONCURRENT_JOBS muito alto (máximo recomendado: 50)")

# Executar validações na importação
validate_settings()