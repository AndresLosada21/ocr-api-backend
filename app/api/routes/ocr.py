# app/api/routes/ocr.py
"""
Endpoints para processamento de OCR (Optical Character Recognition).
Processa imagens para extrair texto usando PaddleOCR.
"""
import time
import tempfile
import os
from typing import Dict, Any, Optional, List
from uuid import uuid4
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl, validator

from app.config.database import get_db
from app.config.settings import settings
from app.core.ocr_service import OCRService
from app.core.image_processor import ImageProcessor
from app.models.database.processing_job import ProcessingJob, JobType, JobStatus
from app.utils.exceptions import (
    OCRAPIException, ValidationError, InvalidImageFormat, 
    ImageTooLarge, ProcessingError
)
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Schemas Pydantic para requests
class OCRProcessURLRequest(BaseModel):
    """Schema para processar OCR via URL."""
    image_url: HttpUrl
    language: str = "pt"
    detect_orientation: bool = True
    return_confidence: bool = False
    enhance_image: bool = True
    
    @validator('language')
    def validate_language(cls, v):
        supported = ['pt', 'en', 'es']  # Expandir conforme necessário
        if v not in supported:
            raise ValueError(f'Idioma deve ser um de: {supported}')
        return v

def validate_uploaded_file(file: UploadFile) -> None:
    """
    Valida arquivo de upload.
    
    Args:
        file: Arquivo enviado via FastAPI
        
    Raises:
        ValidationError: Se arquivo inválido
    """
    # Verificar se arquivo foi enviado
    if not file.filename:
        raise ValidationError("Nenhum arquivo foi enviado")
    
    # Verificar extensão
    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise InvalidImageFormat(file_ext, settings.ALLOWED_EXTENSIONS)
    
    # Verificar tamanho (FastAPI já faz isso, mas vamos garantir)
    if hasattr(file, 'size') and file.size > settings.max_image_size_bytes:
        raise ImageTooLarge(file.size, settings.max_image_size_bytes)

def save_uploaded_file(file: UploadFile) -> str:
    """
    Salva arquivo temporário para processamento.
    
    Args:
        file: Arquivo enviado
        
    Returns:
        Caminho do arquivo temporário
    """
    # Criar diretório temporário se não existir
    temp_dir = settings.create_temp_dir()
    
    # Gerar nome único para o arquivo
    file_ext = file.filename.split('.')[-1].lower()
    temp_filename = f"{uuid4()}.{file_ext}"
    temp_path = temp_dir / temp_filename
    
    # Salvar arquivo
    try:
        with open(temp_path, "wb") as temp_file:
            content = file.file.read()
            temp_file.write(content)
        
        return str(temp_path)
    except Exception as e:
        # Limpar arquivo em caso de erro
        if temp_path.exists():
            temp_path.unlink()
        raise ProcessingError(f"Erro ao salvar arquivo: {str(e)}")

def cleanup_temp_file(file_path: str) -> None:
    """
    Remove arquivo temporário após processamento.
    
    Args:
        file_path: Caminho do arquivo a ser removido
    """
    if settings.CLEANUP_TEMP_FILES:
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
        except Exception as e:
            logger.warning(f"Erro ao remover arquivo temporário: {str(e)}")

@router.post("/ocr/process", tags=["OCR"])
async def process_ocr(
    file: UploadFile = File(..., description="Arquivo de imagem para OCR"),
    language: str = Form("pt", description="Idioma para reconhecimento"),
    detect_orientation: bool = Form(True, description="Detectar orientação da imagem"),
    return_confidence: bool = Form(False, description="Retornar scores de confiança"),
    enhance_image: bool = Form(True, description="Aplicar melhorias na imagem"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Processa uma imagem para extrair texto via OCR.
    
    Args:
        file: Arquivo de imagem (JPG, PNG, PDF, BMP, TIFF)
        language: Idioma para reconhecimento (pt, en, es)
        detect_orientation: Se deve detectar e corrigir orientação
        return_confidence: Se deve retornar scores de confiança
        enhance_image: Se deve aplicar melhorias na imagem
        db: Sessão do banco de dados
        
    Returns:
        Resultados do OCR com job_id para tracking
    """
    start_time = time.time()
    job_id = uuid4()
    temp_file_path = None
    
    # Criar job no banco
    job = ProcessingJob(
        id=job_id,
        job_type=JobType.OCR,
        status=JobStatus.PENDING,
        input_filename=file.filename,
        input_format=file.filename.split('.')[-1].lower() if file.filename else None,
        processing_params={
            "language": language,
            "detect_orientation": detect_orientation,
            "return_confidence": return_confidence,
            "enhance_image": enhance_image
        }
    )
    
    try:
        # Validar arquivo
        validate_uploaded_file(file)
        
        # Obter tamanho do arquivo
        file.file.seek(0, 2)  # Ir para o final
        file_size = file.file.tell()
        file.file.seek(0)  # Voltar ao início
        
        job.input_size_bytes = file_size
        
        # Salvar job no banco
        db.add(job)
        db.commit()
        
        logger.info(
            f"Iniciando processamento OCR",
            extra={
                "job_id": str(job_id),
                "input_filename": file.filename,
                "size_bytes": file_size,
                "language": language
            }
        )
        
        # Salvar arquivo temporário
        temp_file_path = save_uploaded_file(file)
        
        # Processar imagem (se necessário)
        if enhance_image:
            image_processor = ImageProcessor()
            processed_image = image_processor.load_and_process(
                temp_file_path, 
                enhance=True, 
                resize=True
            )
            # Salvar imagem processada
            import cv2
            cv2.imwrite(temp_file_path, processed_image)
        
        # Marcar job como em processamento
        job.start_processing()
        db.commit()
        
        # Executar OCR
        ocr_service = OCRService()
        ocr_results = ocr_service.process_image(
            image_path=temp_file_path,
            language=language,
            return_confidence=return_confidence
        )
        
        # Calcular tempo de processamento
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Preparar resultados
        results = {
            "job_id": str(job_id),
            "job_type": "ocr",
            "status": "completed",
            "text_blocks": ocr_results["text_blocks"],
            "full_text": ocr_results["full_text"],
            "language_detected": ocr_results["language_detected"],
            "processing_time_ms": processing_time_ms,
            "created_at": job.created_at.isoformat()
        }
        
        # Marcar job como concluído
        job.complete_successfully(ocr_results, processing_time_ms)
        db.commit()
        
        logger.info(
            f"OCR processado com sucesso",
            extra={
                "job_id": str(job_id),
                "processing_time_ms": processing_time_ms,
                "text_blocks_count": len(ocr_results["text_blocks"]),
                "total_characters": len(ocr_results["full_text"])
            }
        )
        
        # Preparar metadata
        metadata = {
            "input_image": {
                "input_filename": file.filename,
                "size_bytes": file_size,
                "format": job.input_format.upper(),
                "processing_applied": {
                    "enhancement": enhance_image,
                    "orientation_detection": detect_orientation
                }
            },
            "processing_params": job.processing_params,
            "model_info": {
                "paddle_ocr_version": "2.7.0",  # Versão do requirements
                "language_model": language
            }
        }
        
        return {
            "success": True,
            "data": results,
            "metadata": metadata
        }
        
    except OCRAPIException:
        # Re-raise exceções já tratadas
        raise
    except Exception as e:
        # Tratar erros não esperados
        error_msg = f"Erro durante processamento OCR: {str(e)}"
        logger.error(
            error_msg,
            extra={"job_id": str(job_id), "error": str(e)},
            exc_info=True
        )
        
        # Marcar job como falhou
        if job:
            job.fail_with_error("OCR_PROCESSING_ERROR", error_msg)
            try:
                db.commit()
            except:
                pass
        
        raise ProcessingError(error_msg)
    
    finally:
        # Limpar arquivo temporário
        if temp_file_path:
            cleanup_temp_file(temp_file_path)

@router.post("/ocr/process-url", tags=["OCR"])
async def process_ocr_from_url(
    request: OCRProcessURLRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Processa uma imagem de URL para extrair texto via OCR.
    
    Args:
        request: Dados da requisição com URL e parâmetros
        db: Sessão do banco de dados
        
    Returns:
        Resultados do OCR
    """
    import httpx
    import tempfile
    
    start_time = time.time()
    job_id = uuid4()
    temp_file_path = None
    
    # Criar job no banco
    job = ProcessingJob(
        id=job_id,
        job_type=JobType.OCR,
        status=JobStatus.PENDING,
        input_filename=str(request.image_url),
        processing_params=request.dict()
    )
    
    try:
        # Salvar job no banco
        db.add(job)
        db.commit()
        
        logger.info(
            f"Iniciando processamento OCR via URL",
            extra={
                "job_id": str(job_id),
                "image_url": str(request.image_url)
            }
        )
        
        # Baixar imagem da URL
        async with httpx.AsyncClient() as client:
            response = await client.get(str(request.image_url), timeout=30.0)
            response.raise_for_status()
            
            # Verificar content-type
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                raise ValidationError(f"URL não aponta para uma imagem válida: {content_type}")
            
            # Verificar tamanho
            content_length = int(response.headers.get('content-length', 0))
            if content_length > settings.max_image_size_bytes:
                raise ImageTooLarge(content_length, settings.max_image_size_bytes)
            
            # Salvar em arquivo temporário
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                temp_file.write(response.content)
                temp_file_path = temp_file.name
        
        job.input_size_bytes = len(response.content)
        job.start_processing()
        db.commit()
        
        # Processar com OCR
        ocr_service = OCRService()
        ocr_results = ocr_service.process_image(
            image_path=temp_file_path,
            language=request.language,
            return_confidence=request.return_confidence
        )
        
        # Calcular tempo de processamento
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Preparar resultados
        results = {
            "job_id": str(job_id),
            "job_type": "ocr",
            "status": "completed",
            "text_blocks": ocr_results["text_blocks"],
            "full_text": ocr_results["full_text"],
            "language_detected": ocr_results["language_detected"],
            "processing_time_ms": processing_time_ms,
            "created_at": job.created_at.isoformat()
        }
        
        # Marcar job como concluído
        job.complete_successfully(ocr_results, processing_time_ms)
        db.commit()
        
        logger.info(
            f"OCR via URL processado com sucesso",
            extra={
                "job_id": str(job_id),
                "processing_time_ms": processing_time_ms
            }
        )
        
        return {
            "success": True,
            "data": results,
            "metadata": {
                "input_source": {
                    "url": str(request.image_url),
                    "size_bytes": job.input_size_bytes
                },
                "processing_params": request.dict()
            }
        }
        
    except OCRAPIException:
        raise
    except httpx.HTTPError as e:
        error_msg = f"Erro ao baixar imagem da URL: {str(e)}"
        logger.error(error_msg, extra={"job_id": str(job_id)})
        
        if job:
            job.fail_with_error("URL_DOWNLOAD_ERROR", error_msg)
            try:
                db.commit()
            except:
                pass
        
        raise ValidationError(error_msg)
    except Exception as e:
        error_msg = f"Erro durante processamento OCR via URL: {str(e)}"
        logger.error(
            error_msg,
            extra={"job_id": str(job_id)},
            exc_info=True
        )
        
        if job:
            job.fail_with_error("OCR_PROCESSING_ERROR", error_msg)
            try:
                db.commit()
            except:
                pass
        
        raise ProcessingError(error_msg)
    
    finally:
        # Limpar arquivo temporário
        if temp_file_path:
            cleanup_temp_file(temp_file_path)

@router.get("/ocr/languages", tags=["OCR"])
async def get_supported_languages() -> Dict[str, Any]:
    """
    Retorna lista de idiomas suportados pelo OCR.
    
    Returns:
        Lista de idiomas disponíveis
    """
    try:
        ocr_service = OCRService()
        return {
            "success": True,
            "data": {
                "supported_languages": ocr_service.supported_languages,
                "default_language": settings.PADDLE_OCR_LANG,
                "total_languages": len(ocr_service.supported_languages)
            }
        }
    except Exception as e:
        logger.error(f"Erro ao obter idiomas suportados: {str(e)}")
        raise ProcessingError(f"Erro ao obter idiomas: {str(e)}")

@router.get("/ocr/formats", tags=["OCR"])
async def get_supported_formats() -> Dict[str, Any]:
    """
    Retorna formatos de imagem suportados.
    
    Returns:
        Lista de formatos suportados
    """
    return {
        "success": True,
        "data": {
            "supported_formats": settings.ALLOWED_EXTENSIONS,
            "max_file_size_mb": settings.MAX_IMAGE_SIZE_MB,
            "max_dimensions": settings.MAX_IMAGE_DIMENSION,
            "min_dimensions": settings.MIN_IMAGE_DIMENSION
        }
    }