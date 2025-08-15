# app/main.py - VERSÃO ATUALIZADA COM ROTAS
"""
Aplicação principal FastAPI para OCR API Backend.
Define a aplicação, middlewares, rotas e configurações principais.
"""
import time
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

# Configurações e dependências locais
from app.config.settings import settings
from app.config.database import db_manager, check_db_connection
from app.utils.logger import setup_logging
from app.utils.exceptions import OCRAPIException

# Import dos models primeiro para garantir que estejam registrados
from app.models.database import *

# Import das rotas
from app.api.routes import health, ocr, barcode, qrcode, jobs

# Setup de logging
logger = setup_logging()

class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware para medir tempo de resposta e adicionar headers."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Adicionar Request ID único
        request_id = f"req_{int(start_time * 1000)}"
        request.state.request_id = request_id
        
        try:
            response = await call_next(request)
            
            # Calcular tempo de processamento
            process_time = time.time() - start_time
            
            # Adicionar headers de performance
            response.headers["X-Process-Time"] = f"{process_time:.3f}"
            response.headers["X-Request-ID"] = request_id
            
            # Log da requisição
            logger.info(
                f"{request.method} {request.url.path} - {response.status_code}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "process_time": process_time,
                    "client_ip": request.client.host,
                    "user_agent": request.headers.get("user-agent", ""),
                }
            )
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            
            logger.error(
                f"{request.method} {request.url.path} - Error: {str(e)}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "process_time": process_time,
                    "error": str(e),
                    "client_ip": request.client.host,
                },
                exc_info=True
            )
            
            raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia o ciclo de vida da aplicação.
    Startup e shutdown events.
    """
    # Startup
    logger.info("🚀 Iniciando OCR API Backend")
    logger.info(f"Ambiente: {settings.ENV}")
    logger.info(f"Debug: {settings.DEBUG}")
    logger.info(f"Versão API: {settings.API_VERSION}")
    
    # Verificar conexão com banco
    if check_db_connection():
        logger.info("✅ Conexão com PostgreSQL estabelecida")
        
        # Criar tabelas se não existirem
        try:
            from app.config.database import create_tables
            create_tables()
            logger.info("✅ Tabelas do banco de dados criadas/verificadas")
        except Exception as e:
            logger.error(f"❌ Erro ao criar tabelas: {str(e)}")
            if settings.is_production:
                raise RuntimeError(f"Falha na criação das tabelas: {str(e)}")
    else:
        logger.error("❌ Falha na conexão com PostgreSQL")
        if settings.is_production:
            raise RuntimeError("Não foi possível conectar ao banco de dados")
    
    # Criar diretórios necessários
    settings.create_temp_dir()
    settings.create_log_dir()
    logger.info("📁 Diretórios necessários criados")
    
    # Testar serviços (opcional, para garantir que estão funcionando)
    try:
        from app.core.ocr_service import OCRService
        from app.core.barcode_service import BarcodeService
        from app.core.qrcode_service import QRCodeService
        
        # Inicializar serviços para verificar se estão funcionando
        if settings.ENABLE_OCR:
            OCRService()
            logger.info("✅ Serviço OCR inicializado")
        
        if settings.ENABLE_BARCODE:
            BarcodeService()
            logger.info("✅ Serviço Barcode inicializado")
        
        if settings.ENABLE_QRCODE:
            QRCodeService()
            logger.info("✅ Serviço QR Code inicializado")
            
    except Exception as e:
        logger.warning(f"⚠️ Erro na inicialização de serviços: {str(e)}")
        if settings.is_production:
            raise
    
    yield
    
    # Shutdown
    logger.info("🔄 Finalizando aplicação...")
    db_manager.close_all_connections()
    logger.info("✅ Aplicação finalizada")

# Criar aplicação FastAPI
app = FastAPI(
    title="OCR API Backend",
    description="API Backend para processamento de OCR, Códigos de Barras e QR Codes",
    version=settings.API_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

# ======================
# MIDDLEWARES
# ======================

# Middleware de timing (deve ser o primeiro)
app.add_middleware(TimingMiddleware)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)

# Gzip Middleware (se habilitado)
if settings.ENABLE_GZIP:
    app.add_middleware(GZipMiddleware, minimum_size=1000)

# ======================
# EXCEPTION HANDLERS
# ======================

@app.exception_handler(OCRAPIException)
async def ocr_api_exception_handler(request: Request, exc: OCRAPIException):
    """Handler para exceções customizadas da API."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details
            },
            "timestamp": time.time(),
            "request_id": getattr(request.state, "request_id", None)
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler para erros de validação de dados."""
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Dados de entrada inválidos",
                "details": exc.errors()
            },
            "timestamp": time.time(),
            "request_id": getattr(request.state, "request_id", None)
        }
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handler para exceções HTTP padrão."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "details": None
            },
            "timestamp": time.time(),
            "request_id": getattr(request.state, "request_id", None)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handler para exceções gerais não tratadas."""
    logger.error(
        f"Erro não tratado: {str(exc)}",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "path": request.url.path,
            "method": request.method,
        },
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Erro interno do servidor" if settings.is_production else str(exc),
                "details": None
            },
            "timestamp": time.time(),
            "request_id": getattr(request.state, "request_id", None)
        }
    )

# ======================
# INCLUIR ROTAS
# ======================

# Health Check (sempre ativo)
app.include_router(health.router, tags=["Health Check"])

# Rotas principais da API
if settings.ENABLE_OCR:
    app.include_router(ocr.router, prefix=settings.API_PREFIX, tags=["OCR"])

if settings.ENABLE_BARCODE:
    app.include_router(barcode.router, prefix=settings.API_PREFIX, tags=["Barcode"])

if settings.ENABLE_QRCODE:
    app.include_router(qrcode.router, prefix=settings.API_PREFIX, tags=["QR Code"])

# Jobs e gerenciamento (sempre ativo)
app.include_router(jobs.router, prefix=settings.API_PREFIX, tags=["Jobs"])

# ======================
# ROOT ENDPOINTS
# ======================

@app.get("/", tags=["Info"])
async def root():
    """Endpoint raiz com informações básicas da API."""
    return {
        "name": "OCR API Backend",
        "version": settings.API_VERSION,
        "description": "API para processamento de OCR, Códigos de Barras e QR Codes",
        "status": "running",
        "docs_url": "/docs" if not settings.is_production else "disabled",
        "health_check": "/health",
        "api_prefix": settings.API_PREFIX,
        "endpoints": {
            "health": "/health",
            "ocr": f"{settings.API_PREFIX}/ocr/process" if settings.ENABLE_OCR else "disabled",
            "barcode": f"{settings.API_PREFIX}/barcode/read" if settings.ENABLE_BARCODE else "disabled",
            "qrcode": f"{settings.API_PREFIX}/qrcode/read" if settings.ENABLE_QRCODE else "disabled",
            "jobs": f"{settings.API_PREFIX}/jobs"
        }
    }

@app.get("/api", tags=["Info"])
async def api_info():
    """Informações sobre a API."""
    return {
        "api_version": settings.API_VERSION,
        "supported_formats": settings.ALLOWED_EXTENSIONS,
        "max_file_size_mb": settings.MAX_IMAGE_SIZE_MB,
        "max_concurrent_jobs": settings.MAX_CONCURRENT_JOBS,
        "features": {
            "ocr": settings.ENABLE_OCR,
            "barcode": settings.ENABLE_BARCODE,
            "qrcode": settings.ENABLE_QRCODE,
            "analytics": settings.ENABLE_ANALYTICS,
            "batch_processing": settings.ENABLE_BATCH_PROCESSING
        },
        "limits": {
            "max_image_dimension": settings.MAX_IMAGE_DIMENSION,
            "min_image_dimension": settings.MIN_IMAGE_DIMENSION,
            "job_timeout_seconds": settings.JOB_TIMEOUT_SECONDS
        }
    }

@app.get("/status", tags=["Info"])
async def status():
    """Status rápido da aplicação."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": settings.API_VERSION,
        "environment": settings.ENV
    }

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=1,  # Para desenvolvimento
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True,
    )