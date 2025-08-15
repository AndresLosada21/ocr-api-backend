# app/api/routes/barcode.py
"""
Endpoints para leitura de códigos de barras.
Suporta diversos tipos: EAN13, CODE128, CODE39, etc.
"""
import time
import os
from typing import Dict, Any, Optional, List
from uuid import uuid4
from fastapi import APIRouter, File, UploadFile, Form, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, validator

from app.config.database import get_db
from app.config.settings import settings
from app.core.barcode_service import BarcodeService
from app.core.image_processor import ImageProcessor
from app.models.database.processing_job import ProcessingJob, JobType, JobStatus
from app.utils.exceptions import (
    OCRAPIException, ValidationError, InvalidImageFormat, 
    ImageTooLarge, ProcessingError
)
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Schemas para requests
class BarcodeReadRequest(BaseModel):
    """Schema para configurações de leitura de barcode."""
    barcode_types: Optional[List[str]] = None
    enhance_image: bool = True
    
    @validator('barcode_types')
    def validate_barcode_types(cls, v):
        if v is not None:
            # Tipos suportados pelo pyzbar
            valid_types = [
                'EAN13', 'EAN8', 'CODE128', 'CODE39', 'CODE93', 
                'CODABAR', 'ITF', 'QRCODE', 'PDF417', 'DATAMATRIX'
            ]
            for barcode_type in v:
                if barcode_type.upper() not in valid_types:
                    raise ValueError(f'Tipo de barcode inválido: {barcode_type}. Tipos válidos: {valid_types}')
        return v

def validate_uploaded_file(file: UploadFile) -> None:
    """Valida arquivo de upload."""
    if not file.filename:
        raise ValidationError("Nenhum arquivo foi enviado")
    
    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise InvalidImageFormat(file_ext, settings.ALLOWED_EXTENSIONS)

def save_uploaded_file(file: UploadFile) -> str:
    """Salva arquivo temporário para processamento."""
    temp_dir = settings.create_temp_dir()
    file_ext = file.filename.split('.')[-1].lower()
    temp_filename = f"{uuid4()}.{file_ext}"
    temp_path = temp_dir / temp_filename
    
    try:
        with open(temp_path, "wb") as temp_file:
            content = file.file.read()
            temp_file.write(content)
        return str(temp_path)
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        raise ProcessingError(f"Erro ao salvar arquivo: {str(e)}")

def cleanup_temp_file(file_path: str) -> None:
    """Remove arquivo temporário após processamento."""
    if settings.CLEANUP_TEMP_FILES:
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
        except Exception as e:
            logger.warning(f"Erro ao remover arquivo temporário: {str(e)}")

@router.post("/barcode/read", tags=["Barcode"])
async def read_barcodes(
    file: UploadFile = File(..., description="Arquivo de imagem com códigos de barras"),
    barcode_types: Optional[str] = Form(None, description="Tipos específicos separados por vírgula (ex: EAN13,CODE128)"),
    enhance_image: bool = Form(True, description="Aplicar melhorias na imagem"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Lê códigos de barras em uma imagem.
    
    Args:
        file: Arquivo de imagem contendo códigos de barras
        barcode_types: Lista de tipos específicos para filtrar (opcional)
        enhance_image: Se deve aplicar melhorias na imagem
        db: Sessão do banco de dados
        
    Returns:
        Resultados dos códigos de barras encontrados
    """
    start_time = time.time()
    job_id = uuid4()
    temp_file_path = None
    
    # Processar tipos de barcode se fornecidos
    types_list = None
    if barcode_types:
        types_list = [t.strip().upper() for t in barcode_types.split(',')]
    
    # Criar job no banco
    job = ProcessingJob(
        id=job_id,
        job_type=JobType.BARCODE,
        status=JobStatus.PENDING,
        input_filename=file.filename,
        input_format=file.filename.split('.')[-1].lower() if file.filename else None,
        processing_params={
            "barcode_types": types_list,
            "enhance_image": enhance_image
        }
    )
    
    try:
        # Validar arquivo
        validate_uploaded_file(file)
        
        # Obter tamanho do arquivo
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        
        job.input_size_bytes = file_size
        
        # Salvar job no banco
        db.add(job)
        db.commit()
        
        logger.info(
            f"Iniciando processamento de códigos de barras",
            extra={
                "job_id": str(job_id),
                "input_filename": file.filename,
                "size_bytes": file_size,
                "barcode_types": types_list
            }
        )
        
        # Salvar arquivo temporário
        temp_file_path = save_uploaded_file(file)
        
        # Processar imagem se necessário
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
        
        # Executar leitura de códigos de barras
        barcode_service = BarcodeService()
        barcode_results = barcode_service.read_barcodes(
            image_path=temp_file_path,
            barcode_types=types_list
        )
        
        # Calcular tempo de processamento
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Preparar resultados
        results = {
            "job_id": str(job_id),
            "job_type": "barcode",
            "status": "completed",
            "barcodes": barcode_results["barcodes"],
            "count": barcode_results["count"],
            "processing_time_ms": processing_time_ms,
            "created_at": job.created_at.isoformat()
        }
        
        # Marcar job como concluído
        job.complete_successfully(barcode_results, processing_time_ms)
        db.commit()
        
        logger.info(
            f"Códigos de barras processados com sucesso",
            extra={
                "job_id": str(job_id),
                "processing_time_ms": processing_time_ms,
                "barcodes_found": barcode_results["count"]
            }
        )
        
        # Preparar metadata
        metadata = {
            "input_image": {
                "input_filename": file.filename,
                "size_bytes": file_size,
                "format": job.input_format.upper(),
                "processing_applied": {
                    "enhancement": enhance_image
                }
            },
            "processing_params": job.processing_params
        }
        
        return {
            "success": True,
            "data": results,
            "metadata": metadata
        }
        
    except OCRAPIException:
        raise
    except Exception as e:
        error_msg = f"Erro durante leitura de códigos de barras: {str(e)}"
        logger.error(
            error_msg,
            extra={"job_id": str(job_id), "error": str(e)},
            exc_info=True
        )
        
        if job:
            job.fail_with_error("BARCODE_PROCESSING_ERROR", error_msg)
            try:
                db.commit()
            except:
                pass
        
        raise ProcessingError(error_msg)
    
    finally:
        if temp_file_path:
            cleanup_temp_file(temp_file_path)

@router.get("/barcode/types", tags=["Barcode"])
async def get_supported_barcode_types() -> Dict[str, Any]:
    """
    Retorna tipos de códigos de barras suportados.
    
    Returns:
        Lista de tipos de barcode disponíveis
    """
    try:
        barcode_service = BarcodeService()
        return {
            "success": True,
            "data": {
                "supported_types": barcode_service.supported_types,
                "total_types": len(barcode_service.supported_types),
                "examples": {
                    "EAN13": "Código de barras padrão de produtos (13 dígitos)",
                    "CODE128": "Código alfanumérico de alta densidade",
                    "CODE39": "Código alfanumérico simples",
                    "QR_CODE": "QR Code (também detectado aqui)"
                }
            }
        }
    except Exception as e:
        logger.error(f"Erro ao obter tipos de barcode: {str(e)}")
        raise ProcessingError(f"Erro ao obter tipos: {str(e)}")

@router.post("/barcode/batch", tags=["Barcode"])
async def read_barcodes_batch(
    files: List[UploadFile] = File(..., description="Múltiplos arquivos de imagem"),
    barcode_types: Optional[str] = Form(None, description="Tipos específicos para todos os arquivos"),
    enhance_image: bool = Form(True, description="Aplicar melhorias nas imagens"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Processa múltiplas imagens para leitura de códigos de barras.
    
    Args:
        files: Lista de arquivos de imagem
        barcode_types: Tipos de barcode para filtrar
        enhance_image: Aplicar melhorias nas imagens
        db: Sessão do banco de dados
        
    Returns:
        Resultados de todos os arquivos processados
    """
    if not settings.ENABLE_BATCH_PROCESSING:
        raise ValidationError("Processamento em lote não está habilitado")
    
    if len(files) > 10:  # Limite razoável
        raise ValidationError("Máximo de 10 arquivos por lote")
    
    start_time = time.time()
    batch_id = uuid4()
    results = []
    
    # Processar tipos de barcode
    types_list = None
    if barcode_types:
        types_list = [t.strip().upper() for t in barcode_types.split(',')]
    
    logger.info(
        f"Iniciando processamento em lote",
        extra={
            "batch_id": str(batch_id),
            "files_count": len(files),
            "barcode_types": types_list
        }
    )
    
    for i, file in enumerate(files):
        temp_file_path = None
        try:
            # Processar cada arquivo individualmente
            job_id = uuid4()
            
            # Validar arquivo
            validate_uploaded_file(file)
            
            # Criar job
            job = ProcessingJob(
                id=job_id,
                job_type=JobType.BARCODE,
                status=JobStatus.PENDING,
                input_filename=file.filename,
                input_format=file.filename.split('.')[-1].lower() if file.filename else None,
                processing_params={
                    "barcode_types": types_list,
                    "enhance_image": enhance_image,
                    "batch_id": str(batch_id),
                    "batch_index": i
                }
            )
            
            file.file.seek(0, 2)
            job.input_size_bytes = file.file.tell()
            file.file.seek(0)
            
            db.add(job)
            db.commit()
            
            # Salvar e processar arquivo
            temp_file_path = save_uploaded_file(file)
            
            if enhance_image:
                image_processor = ImageProcessor()
                processed_image = image_processor.load_and_process(temp_file_path)
                import cv2
                cv2.imwrite(temp_file_path, processed_image)
            
            job.start_processing()
            db.commit()
            
            # Processar códigos de barras
            barcode_service = BarcodeService()
            barcode_results = barcode_service.read_barcodes(temp_file_path, types_list)
            
            # Marcar como concluído
            processing_time = int((time.time() - start_time) * 1000)
            job.complete_successfully(barcode_results, processing_time)
            db.commit()
            
            # Adicionar aos resultados
            results.append({
                "job_id": str(job_id),
                "input_filename": file.filename,
                "status": "completed",
                "barcodes": barcode_results["barcodes"],
                "count": barcode_results["count"]
            })
            
        except Exception as e:
            logger.error(f"Erro no arquivo {file.filename}: {str(e)}")
            results.append({
                "job_id": str(job_id) if 'job_id' in locals() else None,
                "input_filename": file.filename,
                "status": "failed",
                "error": str(e)
            })
        
        finally:
            if temp_file_path:
                cleanup_temp_file(temp_file_path)
    
    total_time = int((time.time() - start_time) * 1000)
    
    # Estatísticas do lote
    successful = len([r for r in results if r["status"] == "completed"])
    failed = len(results) - successful
    total_barcodes = sum(r.get("count", 0) for r in results if "count" in r)
    
    logger.info(
        f"Lote processado",
        extra={
            "batch_id": str(batch_id),
            "total_files": len(files),
            "successful": successful,
            "failed": failed,
            "total_barcodes": total_barcodes,
            "total_time_ms": total_time
        }
    )
    
    return {
        "success": True,
        "data": {
            "batch_id": str(batch_id),
            "total_files": len(files),
            "successful_files": successful,
            "failed_files": failed,
            "total_barcodes_found": total_barcodes,
            "processing_time_ms": total_time,
            "results": results
        }
    }