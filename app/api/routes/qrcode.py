# app/api/routes/qrcode.py
"""
Endpoints para leitura de códigos QR.
Detecta e decodifica QR codes em imagens.
"""
import time
import os
from typing import Dict, Any, List
from uuid import uuid4
from fastapi import APIRouter, File, UploadFile, Form, Depends
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.config.settings import settings
from app.core.qrcode_service import QRCodeService
from app.core.image_processor import ImageProcessor
from app.models.database.processing_job import ProcessingJob, JobType, JobStatus
from app.utils.exceptions import (
    OCRAPIException, ValidationError, InvalidImageFormat, 
    ImageTooLarge, ProcessingError
)
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

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

def classify_qr_data(data: str) -> str:
    """
    Classifica o tipo de dados do QR code.
    
    Args:
        data: Dados decodificados do QR
        
    Returns:
        Tipo classificado (url, email, phone, text, etc.)
    """
    data_lower = data.lower().strip()
    
    if data_lower.startswith(('http://', 'https://', 'www.')):
        return "url"
    elif data_lower.startswith('mailto:'):
        return "email"
    elif data_lower.startswith('tel:'):
        return "phone"
    elif data_lower.startswith('sms:'):
        return "sms"
    elif data_lower.startswith('wifi:'):
        return "wifi"
    elif data_lower.startswith('geo:'):
        return "location"
    elif '@' in data and '.' in data:
        return "email"
    elif data.replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '').isdigit():
        return "phone"
    else:
        return "text"

@router.post("/qrcode/read", tags=["QR Code"])
async def read_qrcodes(
    file: UploadFile = File(..., description="Arquivo de imagem com códigos QR"),
    multiple: bool = Form(False, description="Detectar múltiplos QR codes"),
    enhance_image: bool = Form(True, description="Aplicar melhorias na imagem"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Lê códigos QR em uma imagem.
    
    Args:
        file: Arquivo de imagem contendo códigos QR
        multiple: Se deve detectar múltiplos QR codes
        enhance_image: Se deve aplicar melhorias na imagem
        db: Sessão do banco de dados
        
    Returns:
        Resultados dos códigos QR encontrados
    """
    start_time = time.time()
    job_id = uuid4()
    temp_file_path = None
    
    # Criar job no banco
    job = ProcessingJob(
        id=job_id,
        job_type=JobType.QRCODE,
        status=JobStatus.PENDING,
        input_filename=file.filename,
        input_format=file.filename.split('.')[-1].lower() if file.filename else None,
        processing_params={
            "multiple": multiple,
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
            f"Iniciando processamento de códigos QR",
            extra={
                "job_id": str(job_id),
                "input_filename": file.filename,
                "size_bytes": file_size,
                "multiple": multiple
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
        
        # Executar leitura de QR codes
        qr_service = QRCodeService()
        qr_results = qr_service.read_qrcodes(
            image_path=temp_file_path,
            multiple=multiple
        )
        
        # Enriquecer resultados com classificação de dados
        for qr_code in qr_results["qr_codes"]:
            qr_code["data_type"] = classify_qr_data(qr_code["data"])
            
            # Adicionar informações extras baseadas no tipo
            if qr_code["data_type"] == "url":
                qr_code["url_info"] = {
                    "is_https": qr_code["data"].startswith("https://"),
                    "domain": qr_code["data"].split("//")[1].split("/")[0] if "//" in qr_code["data"] else None
                }
            elif qr_code["data_type"] == "wifi":
                # Parse básico de configuração WiFi
                try:
                    parts = qr_code["data"].split(";")
                    wifi_info = {}
                    for part in parts:
                        if ":" in part:
                            key, value = part.split(":", 1)
                            wifi_info[key.lower()] = value
                    qr_code["wifi_info"] = wifi_info
                except:
                    pass
        
        # Calcular tempo de processamento
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Preparar resultados
        results = {
            "job_id": str(job_id),
            "job_type": "qrcode",
            "status": "completed",
            "qr_codes": qr_results["qr_codes"],
            "count": qr_results["count"],
            "processing_time_ms": processing_time_ms,
            "created_at": job.created_at.isoformat()
        }
        
        # Marcar job como concluído
        job.complete_successfully(qr_results, processing_time_ms)
        db.commit()
        
        logger.info(
            f"Códigos QR processados com sucesso",
            extra={
                "job_id": str(job_id),
                "processing_time_ms": processing_time_ms,
                "qr_codes_found": qr_results["count"]
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
                    "multiple_detection": multiple
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
        error_msg = f"Erro durante leitura de códigos QR: {str(e)}"
        logger.error(
            error_msg,
            extra={"job_id": str(job_id), "error": str(e)},
            exc_info=True
        )
        
        if job:
            job.fail_with_error("QRCODE_PROCESSING_ERROR", error_msg)
            try:
                db.commit()
            except:
                pass
        
        raise ProcessingError(error_msg)
    
    finally:
        if temp_file_path:
            cleanup_temp_file(temp_file_path)

@router.post("/qrcode/generate", tags=["QR Code"])
async def generate_qrcode(
    data: str = Form(..., description="Dados para codificar no QR code"),
    size: int = Form(200, description="Tamanho da imagem em pixels"),
    error_correction: str = Form("M", description="Nível de correção de erro (L, M, Q, H)"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Gera um código QR com os dados fornecidos.
    
    Args:
        data: Dados para codificar
        size: Tamanho da imagem
        error_correction: Nível de correção de erro
        db: Sessão do banco de dados
        
    Returns:
        QR code gerado em base64
    """
    import qrcode
    import io
    import base64
    from PIL import Image
    
    start_time = time.time()
    job_id = uuid4()
    
    # Validar parâmetros
    if len(data) > 2000:  # Limite razoável para QR codes
        raise ValidationError("Dados muito longos para QR code (máximo 2000 caracteres)")
    
    if size < 50 or size > 1000:
        raise ValidationError("Tamanho deve estar entre 50 e 1000 pixels")
    
    error_levels = {"L": qrcode.constants.ERROR_CORRECT_L,
                   "M": qrcode.constants.ERROR_CORRECT_M,
                   "Q": qrcode.constants.ERROR_CORRECT_Q,
                   "H": qrcode.constants.ERROR_CORRECT_H}
    
    if error_correction not in error_levels:
        raise ValidationError("Nível de correção deve ser L, M, Q ou H")
    
    # Criar job no banco
    job = ProcessingJob(
        id=job_id,
        job_type=JobType.QRCODE,
        status=JobStatus.PENDING,
        input_filename="qr_generation",
        processing_params={
            "data": data[:100] + "..." if len(data) > 100 else data,  # Truncar para log
            "size": size,
            "error_correction": error_correction,
            "operation": "generate"
        }
    )
    
    try:
        db.add(job)
        db.commit()
        
        logger.info(
            f"Gerando código QR",
            extra={
                "job_id": str(job_id),
                "data_length": len(data),
                "size": size,
                "error_correction": error_correction
            }
        )
        
        job.start_processing()
        db.commit()
        
        # Gerar QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=error_levels[error_correction],
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        # Criar imagem
        img = qr.make_image(fill_color="black", back_color="white")
        img = img.resize((size, size), Image.Resampling.LANCZOS)
        
        # Converter para base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Preparar resultados
        results = {
            "job_id": str(job_id),
            "job_type": "qrcode_generation",
            "status": "completed",
            "qr_code": {
                "data": data,
                "data_type": classify_qr_data(data),
                "image_base64": img_base64,
                "size": size,
                "error_correction": error_correction,
                "format": "PNG"
            },
            "processing_time_ms": processing_time_ms,
            "created_at": job.created_at.isoformat()
        }
        
        # Marcar job como concluído
        job.complete_successfully(results, processing_time_ms)
        db.commit()
        
        logger.info(
            f"QR code gerado com sucesso",
            extra={
                "job_id": str(job_id),
                "processing_time_ms": processing_time_ms,
                "image_size": len(img_base64)
            }
        )
        
        return {
            "success": True,
            "data": results
        }
        
    except Exception as e:
        error_msg = f"Erro durante geração de QR code: {str(e)}"
        logger.error(
            error_msg,
            extra={"job_id": str(job_id), "error": str(e)},
            exc_info=True
        )
        
        if job:
            job.fail_with_error("QRCODE_GENERATION_ERROR", error_msg)
            try:
                db.commit()
            except:
                pass
        
        raise ProcessingError(error_msg)

@router.post("/qrcode/batch", tags=["QR Code"])
async def read_qrcodes_batch(
    files: List[UploadFile] = File(..., description="Múltiplos arquivos de imagem"),
    multiple: bool = Form(False, description="Detectar múltiplos QR codes por imagem"),
    enhance_image: bool = Form(True, description="Aplicar melhorias nas imagens"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Processa múltiplas imagens para leitura de códigos QR.
    
    Args:
        files: Lista de arquivos de imagem
        multiple: Detectar múltiplos QR codes por imagem
        enhance_image: Aplicar melhorias nas imagens
        db: Sessão do banco de dados
        
    Returns:
        Resultados de todos os arquivos processados
    """
    if not settings.ENABLE_BATCH_PROCESSING:
        raise ValidationError("Processamento em lote não está habilitado")
    
    if len(files) > 10:
        raise ValidationError("Máximo de 10 arquivos por lote")
    
    start_time = time.time()
    batch_id = uuid4()
    results = []
    
    logger.info(
        f"Iniciando processamento em lote de QR codes",
        extra={
            "batch_id": str(batch_id),
            "files_count": len(files),
            "multiple": multiple
        }
    )
    
    for i, file in enumerate(files):
        temp_file_path = None
        try:
            job_id = uuid4()
            
            # Validar arquivo
            validate_uploaded_file(file)
            
            # Criar job
            job = ProcessingJob(
                id=job_id,
                job_type=JobType.QRCODE,
                status=JobStatus.PENDING,
                input_filename=file.filename,
                input_format=file.filename.split('.')[-1].lower() if file.filename else None,
                processing_params={
                    "multiple": multiple,
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
            
            # Processar QR codes
            qr_service = QRCodeService()
            qr_results = qr_service.read_qrcodes(temp_file_path, multiple)
            
            # Enriquecer com classificação
            for qr_code in qr_results["qr_codes"]:
                qr_code["data_type"] = classify_qr_data(qr_code["data"])
            
            # Marcar como concluído
            processing_time = int((time.time() - start_time) * 1000)
            job.complete_successfully(qr_results, processing_time)
            db.commit()
            
            # Adicionar aos resultados
            results.append({
                "job_id": str(job_id),
                "input_filename": file.filename,
                "status": "completed",
                "qr_codes": qr_results["qr_codes"],
                "count": qr_results["count"]
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
    total_qrcodes = sum(r.get("count", 0) for r in results if "count" in r)
    
    logger.info(
        f"Lote de QR codes processado",
        extra={
            "batch_id": str(batch_id),
            "total_files": len(files),
            "successful": successful,
            "failed": failed,
            "total_qrcodes": total_qrcodes,
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
            "total_qrcodes_found": total_qrcodes,
            "processing_time_ms": total_time,
            "results": results
        }
    }

@router.get("/qrcode/info", tags=["QR Code"])
async def get_qrcode_info() -> Dict[str, Any]:
    """
    Retorna informações sobre capacidades de QR codes.
    
    Returns:
        Informações sobre tipos e limites de QR codes
    """
    return {
        "success": True,
        "data": {
            "supported_data_types": [
                "text", "url", "email", "phone", "sms", 
                "wifi", "location", "contact"
            ],
            "max_data_length": 2000,
            "error_correction_levels": {
                "L": "Low (~7% recovery)",
                "M": "Medium (~15% recovery)", 
                "Q": "Quartile (~25% recovery)",
                "H": "High (~30% recovery)"
            },
            "image_formats": ["PNG", "JPEG"],
            "size_limits": {
                "min_pixels": 50,
                "max_pixels": 1000,
                "recommended": 200
            },
            "examples": {
                "url": "https://example.com",
                "email": "mailto:user@example.com",
                "phone": "tel:+5511999999999",
                "wifi": "WIFI:T:WPA;S:NetworkName;P:Password;;"
            }
        }
    }