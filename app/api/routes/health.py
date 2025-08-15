# app/api/routes/health.py
"""
Endpoint de verificação de saúde da aplicação.
Verifica status de todos os serviços e componentes.
"""
import time
import psutil
import os
from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config.database import get_db, db_manager
from app.config.settings import settings
from app.core.ocr_service import OCRService
from app.core.barcode_service import BarcodeService
from app.core.qrcode_service import QRCodeService
from app.utils.exceptions import OCRAPIException

router = APIRouter()

@router.get("/health", tags=["Health Check"])
async def health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Endpoint de verificação de saúde da aplicação.
    Verifica status de todos os serviços e componentes.
    
    Returns:
        Dict com status detalhado de todos os componentes
    """
    start_time = time.time()
    
    # Status geral (será atualizado se algum serviço falhar)
    overall_status = "healthy"
    services = {}
    
    # ======================
    # VERIFICAR BANCO DE DADOS
    # ======================
    try:
        db_health = db_manager.health_check()
        services["database"] = db_health
        
        if db_health.get("status") != "healthy":
            overall_status = "unhealthy"
    except Exception as e:
        services["database"] = {
            "status": "error",
            "error": str(e)
        }
        overall_status = "unhealthy"
    
    # ======================
    # VERIFICAR PADDLE OCR
    # ======================
    try:
        ocr_service = OCRService()
        services["paddle_ocr"] = {
            "status": "ready",
            "model_loaded": ocr_service.paddle_ocr is not None,
            "supported_languages": ocr_service.supported_languages
        }
    except Exception as e:
        services["paddle_ocr"] = {
            "status": "error",
            "model_loaded": False,
            "error": str(e),
            "supported_languages": []
        }
        overall_status = "unhealthy"
    
    # ======================
    # VERIFICAR BARCODE READER
    # ======================
    try:
        barcode_service = BarcodeService()
        services["barcode_reader"] = {
            "status": "ready",
            "supported_types": barcode_service.supported_types
        }
    except Exception as e:
        services["barcode_reader"] = {
            "status": "error",
            "error": str(e),
            "supported_types": []
        }
        overall_status = "unhealthy"
    
    # ======================
    # VERIFICAR QR READER
    # ======================
    try:
        qr_service = QRCodeService()
        services["qr_reader"] = {
            "status": "ready"
        }
    except Exception as e:
        services["qr_reader"] = {
            "status": "error",
            "error": str(e)
        }
        overall_status = "unhealthy"
    
    # ======================
    # INFORMAÇÕES DO SISTEMA
    # ======================
    try:
        system_info = {
            "cpu_usage": psutil.cpu_percent(interval=1),
            "memory_usage": psutil.virtual_memory().percent / 100,
            "disk_usage": psutil.disk_usage('/').percent / 100,
            "uptime_seconds": time.time() - start_time,
            "process_id": os.getpid(),
            "python_version": f"{psutil.sys.version_info.major}.{psutil.sys.version_info.minor}.{psutil.sys.version_info.micro}"
        }
    except Exception as e:
        system_info = {
            "error": f"Erro ao obter informações do sistema: {str(e)}"
        }
    
    # ======================
    # CONFIGURAÇÕES DA APLICAÇÃO
    # ======================
    app_settings = {
        "max_image_size_mb": settings.MAX_IMAGE_SIZE_MB,
        "max_concurrent_jobs": settings.MAX_CONCURRENT_JOBS,
        "temp_upload_dir": settings.TEMP_UPLOAD_DIR,
        "supported_formats": settings.ALLOWED_EXTENSIONS,
        "features": {
            "ocr_enabled": settings.ENABLE_OCR,
            "barcode_enabled": settings.ENABLE_BARCODE,
            "qrcode_enabled": settings.ENABLE_QRCODE,
            "analytics_enabled": settings.ENABLE_ANALYTICS,
            "batch_processing": settings.ENABLE_BATCH_PROCESSING
        }
    }
    
    # Calcular tempo de resposta
    response_time = (time.time() - start_time) * 1000
    
    return {
        "status": overall_status,
        "timestamp": time.time(),
        "version": settings.API_VERSION,
        "environment": settings.ENV,
        "response_time_ms": round(response_time, 2),
        "services": services,
        "system": system_info,
        "settings": app_settings
    }

@router.get("/health/simple", tags=["Health Check"])
async def simple_health_check() -> Dict[str, str]:
    """
    Health check simples e rápido.
    Usado por load balancers e monitoring básico.
    
    Returns:
        Status básico da aplicação
    """
    return {
        "status": "healthy",
        "service": "ocr-api",
        "version": settings.API_VERSION
    }

@router.get("/health/database", tags=["Health Check"])
async def database_health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Verificação específica da saúde do banco de dados.
    
    Args:
        db: Sessão do banco de dados
        
    Returns:
        Status detalhado do banco
    """
    try:
        # Teste de conexão simples
        from sqlalchemy import text
        start_time = time.time()
        db.execute(text("SELECT 1"))
        query_time = (time.time() - start_time) * 1000
        
        # Estatísticas do pool de conexões
        pool = db_manager.engine.pool
        
        pool_info = {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow()
        }
        
        # Adicionar invalidated apenas se o método existir
        try:
            pool_info["invalidated"] = pool.invalidated()
        except AttributeError:
            pass
        
        return {
            "status": "healthy",
            "response_time_ms": round(query_time, 2),
            "connection_pool": pool_info,
            "database_info": {
                "url": str(db_manager.engine.url).replace(
                    str(db_manager.engine.url.password), "*****"
                ) if db_manager.engine.url.password else str(db_manager.engine.url)
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "error_type": type(e).__name__
        }

@router.get("/health/services", tags=["Health Check"])
async def services_health_check() -> Dict[str, Any]:
    """
    Verificação específica dos serviços de processamento.
    
    Returns:
        Status de OCR, Barcode e QR Code services
    """
    services_status = {}
    
    # Testar OCR Service
    try:
        ocr_service = OCRService()
        services_status["ocr"] = {
            "status": "ready",
            "languages": ocr_service.supported_languages,
            "model_loaded": ocr_service.paddle_ocr is not None
        }
    except Exception as e:
        services_status["ocr"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Testar Barcode Service
    try:
        barcode_service = BarcodeService()
        services_status["barcode"] = {
            "status": "ready",
            "supported_types": barcode_service.supported_types
        }
    except Exception as e:
        services_status["barcode"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Testar QR Code Service
    try:
        qr_service = QRCodeService()
        services_status["qrcode"] = {
            "status": "ready"
        }
    except Exception as e:
        services_status["qrcode"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Determinar status geral
    all_healthy = all(
        service.get("status") == "ready" 
        for service in services_status.values()
    )
    
    return {
        "overall_status": "healthy" if all_healthy else "degraded",
        "services": services_status,
        "timestamp": time.time()
    }