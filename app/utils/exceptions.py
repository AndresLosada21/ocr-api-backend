"""
Exceções customizadas para a OCR API.
Define classes de erro específicas para diferentes cenários.
"""
from typing import Any, Dict, Optional

class OCRAPIException(Exception):
    """
    Exceção base para todas as exceções da OCR API.
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "GENERIC_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

# ======================
# EXCEÇÕES DE VALIDAÇÃO
# ======================

class ValidationError(OCRAPIException):
    """Erro de validação de dados de entrada."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=400,
            details=details
        )

class InvalidImageFormat(ValidationError):
    """Formato de imagem não suportado."""
    
    def __init__(self, format_provided: str, supported_formats: list):
        super().__init__(
            message=f"Formato '{format_provided}' não suportado",
            details={
                "format_provided": format_provided,
                "supported_formats": supported_formats
            }
        )
        self.error_code = "INVALID_IMAGE_FORMAT"

class ImageTooLarge(ValidationError):
    """Imagem excede tamanho máximo permitido."""
    
    def __init__(self, size_bytes: int, max_size_bytes: int):
        size_mb = size_bytes / (1024 * 1024)
        max_size_mb = max_size_bytes / (1024 * 1024)
        
        super().__init__(
            message=f"Imagem muito grande: {size_mb:.1f}MB (máximo: {max_size_mb:.1f}MB)",
            details={
                "size_bytes": size_bytes,
                "max_size_bytes": max_size_bytes,
                "size_mb": size_mb,
                "max_size_mb": max_size_mb
            }
        )
        self.error_code = "IMAGE_TOO_LARGE"

class ImageTooSmall(ValidationError):
    """Imagem menor que tamanho mínimo."""
    
    def __init__(self, width: int, height: int, min_dimension: int):
        super().__init__(
            message=f"Imagem muito pequena: {width}x{height} (mínimo: {min_dimension}px)",
            details={
                "width": width,
                "height": height,
                "min_dimension": min_dimension
            }
        )
        self.error_code = "IMAGE_TOO_SMALL"

class CorruptedImage(ValidationError):
    """Imagem corrompida ou ilegível."""
    
    def __init__(self, details: str = None):
        super().__init__(
            message="Imagem corrompida ou ilegível",
            details={"corruption_details": details} if details else None
        )
        self.error_code = "CORRUPTED_IMAGE"

# ======================
# EXCEÇÕES DE PROCESSAMENTO
# ======================

class ProcessingError(OCRAPIException):
    """Erro durante processamento de imagem."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="PROCESSING_ERROR",
            status_code=500,
            details=details
        )

class OCRProcessingError(ProcessingError):
    """Erro específico de processamento OCR."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.error_code = "OCR_PROCESSING_ERROR"

class BarcodeProcessingError(ProcessingError):
    """Erro específico de processamento de códigos de barras."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.error_code = "BARCODE_PROCESSING_ERROR"

class QRCodeProcessingError(ProcessingError):
    """Erro específico de processamento de QR codes."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.error_code = "QRCODE_PROCESSING_ERROR"

class ModelNotLoaded(ProcessingError):
    """Modelo de ML não foi carregado."""
    
    def __init__(self, model_name: str):
        super().__init__(
            message=f"Modelo '{model_name}' não está carregado",
            details={"model_name": model_name}
        )
        self.error_code = "MODEL_NOT_LOADED"

class ProcessingTimeout(ProcessingError):
    """Timeout durante processamento."""
    
    def __init__(self, timeout_seconds: int):
        super().__init__(
            message=f"Processamento excedeu tempo limite de {timeout_seconds}s",
            details={"timeout_seconds": timeout_seconds}
        )
        self.error_code = "PROCESSING_TIMEOUT"

# ======================
# EXCEÇÕES DE RECURSOS
# ======================

class ResourceError(OCRAPIException):
    """Erro relacionado a recursos do sistema."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="RESOURCE_ERROR",
            status_code=503,
            details=details
        )

class InsufficientMemory(ResourceError):
    """Memória insuficiente para processamento."""
    
    def __init__(self, required_mb: float, available_mb: float):
        super().__init__(
            message=f"Memória insuficiente: requer {required_mb:.1f}MB, disponível {available_mb:.1f}MB",
            details={
                "required_mb": required_mb,
                "available_mb": available_mb
            }
        )
        self.error_code = "INSUFFICIENT_MEMORY"

class TooManyRequests(ResourceError):
    """Muitas requisições simultâneas."""
    
    def __init__(self, current_jobs: int, max_jobs: int):
        super().__init__(
            message=f"Muitas requisições simultâneas: {current_jobs}/{max_jobs}",
            details={
                "current_jobs": current_jobs,
                "max_jobs": max_jobs
            },
            status_code=429
        )
        self.error_code = "TOO_MANY_REQUESTS"

class DiskSpaceError(ResourceError):
    """Espaço em disco insuficiente."""
    
    def __init__(self, available_mb: float, required_mb: float):
        super().__init__(
            message=f"Espaço em disco insuficiente: disponível {available_mb:.1f}MB, necessário {required_mb:.1f}MB",
            details={
                "available_mb": available_mb,
                "required_mb": required_mb
            }
        )
        self.error_code = "DISK_SPACE_ERROR"

# ======================
# EXCEÇÕES DE BANCO DE DADOS
# ======================

class DatabaseError(OCRAPIException):
    """Erro relacionado ao banco de dados."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            status_code=500,
            details=details
        )

class JobNotFound(DatabaseError):
    """Job não encontrado no banco."""
    
    def __init__(self, job_id: str):
        super().__init__(
            message=f"Job não encontrado: {job_id}",
            details={"job_id": job_id},
            status_code=404
        )
        self.error_code = "JOB_NOT_FOUND"

class DatabaseConnectionError(DatabaseError):
    """Erro de conexão com banco de dados."""
    
    def __init__(self, details: str = None):
        super().__init__(
            message="Erro de conexão com banco de dados",
            details={"connection_details": details} if details else None
        )
        self.error_code = "DATABASE_CONNECTION_ERROR"

# ======================
# EXCEÇÕES DE CONFIGURAÇÃO
# ======================

class ConfigurationError(OCRAPIException):
    """Erro de configuração da aplicação."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            status_code=500,
            details=details
        )

class MissingDependency(ConfigurationError):
    """Dependência necessária não encontrada."""
    
    def __init__(self, dependency: str, install_hint: str = None):
        message = f"Dependência necessária não encontrada: {dependency}"
        if install_hint:
            message += f" (instale com: {install_hint})"
        
        super().__init__(
            message=message,
            details={
                "dependency": dependency,
                "install_hint": install_hint
            }
        )
        self.error_code = "MISSING_DEPENDENCY"

# ======================
# UTILIDADES
# ======================

def handle_exception(func):
    """
    Decorator para tratamento automático de exceções.
    Converte exceções padrão em exceções da API.
    """
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except OCRAPIException:
            # Re-raise exceções já tratadas
            raise
        except FileNotFoundError as e:
            raise ValidationError(f"Arquivo não encontrado: {str(e)}")
        except PermissionError as e:
            raise ResourceError(f"Erro de permissão: {str(e)}")
        except MemoryError:
            raise InsufficientMemory(0, 0)  # Valores serão calculados pelo sistema
        except TimeoutError as e:
            raise ProcessingTimeout(30)  # Timeout padrão
        except Exception as e:
            # Log do erro original para debug
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erro não tratado em {func.__name__}: {str(e)}", exc_info=True)
            
            raise ProcessingError(
                f"Erro interno durante {func.__name__}",
                details={"original_error": str(e), "error_type": type(e).__name__}
            )
    
    return wrapper

def validate_image_constraints(
    size_bytes: int,
    width: int,
    height: int,
    format_ext: str,
    allowed_formats: list,
    max_size_bytes: int,
    min_dimension: int,
    max_dimension: int
):
    """
    Valida restrições de imagem e levanta exceções apropriadas.
    
    Args:
        size_bytes: Tamanho em bytes
        width: Largura em pixels
        height: Altura em pixels
        format_ext: Extensão do formato
        allowed_formats: Formatos permitidos
        max_size_bytes: Tamanho máximo em bytes
        min_dimension: Dimensão mínima em pixels
        max_dimension: Dimensão máxima em pixels
    
    Raises:
        InvalidImageFormat: Se formato não suportado
        ImageTooLarge: Se imagem muito grande
        ImageTooSmall: Se imagem muito pequena
    """
    # Validar formato
    if format_ext.lower() not in [fmt.lower() for fmt in allowed_formats]:
        raise InvalidImageFormat(format_ext, allowed_formats)
    
    # Validar tamanho do arquivo
    if size_bytes > max_size_bytes:
        raise ImageTooLarge(size_bytes, max_size_bytes)
    
    # Validar dimensões mínimas
    if width < min_dimension or height < min_dimension:
        raise ImageTooSmall(width, height, min_dimension)
    
    # Validar dimensões máximas
    if width > max_dimension or height > max_dimension:
        raise ValidationError(
            f"Imagem muito grande: {width}x{height} (máximo: {max_dimension}px)",
            details={
                "width": width,
                "height": height,
                "max_dimension": max_dimension
            }
        )