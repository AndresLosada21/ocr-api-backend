# app/api/dependencies.py
"""
Dependências compartilhadas entre endpoints da API.
"""
import time
from typing import Dict, Any, Optional
from fastapi import Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.config.settings import settings
from app.utils.exceptions import ValidationError, TooManyRequests
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Cache simples para rate limiting (em produção usar Redis)
request_cache: Dict[str, Dict[str, Any]] = {}

def get_client_ip(request: Request) -> str:
    """
    Extrai o IP real do cliente considerando proxies.
    
    Args:
        request: Request do FastAPI
        
    Returns:
        IP do cliente
    """
    # Verificar headers de proxy
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback para IP direto
    return request.client.host

def rate_limit_check(
    request: Request,
    requests_per_minute: int = settings.RATE_LIMIT_REQUESTS_PER_MINUTE,
    requests_per_day: int = settings.RATE_LIMIT_REQUESTS_PER_DAY
) -> None:
    """
    Verifica rate limiting baseado no IP do cliente.
    
    Args:
        request: Request do FastAPI
        requests_per_minute: Limite por minuto
        requests_per_day: Limite por dia
        
    Raises:
        TooManyRequests: Se exceder limites
    """
    client_ip = get_client_ip(request)
    current_time = time.time()
    
    # Inicializar dados do cliente se não existir
    if client_ip not in request_cache:
        request_cache[client_ip] = {
            "minute_requests": [],
            "day_requests": [],
            "first_request": current_time
        }
    
    client_data = request_cache[client_ip]
    
    # Limpar requisições antigas (últimos 60 segundos)
    minute_cutoff = current_time - 60
    client_data["minute_requests"] = [
        req_time for req_time in client_data["minute_requests"] 
        if req_time > minute_cutoff
    ]
    
    # Limpar requisições antigas (últimas 24 horas)
    day_cutoff = current_time - (24 * 60 * 60)
    client_data["day_requests"] = [
        req_time for req_time in client_data["day_requests"] 
        if req_time > day_cutoff
    ]
    
    # Verificar limite por minuto
    if len(client_data["minute_requests"]) >= requests_per_minute:
        logger.warning(
            f"Rate limit excedido (minuto): {client_ip}",
            extra={
                "client_ip": client_ip,
                "requests_per_minute": len(client_data["minute_requests"]),
                "limit": requests_per_minute
            }
        )
        raise TooManyRequests(
            len(client_data["minute_requests"]), 
            requests_per_minute
        )
    
    # Verificar limite por dia
    if len(client_data["day_requests"]) >= requests_per_day:
        logger.warning(
            f"Rate limit excedido (dia): {client_ip}",
            extra={
                "client_ip": client_ip,
                "requests_per_day": len(client_data["day_requests"]),
                "limit": requests_per_day
            }
        )
        raise TooManyRequests(
            len(client_data["day_requests"]), 
            requests_per_day
        )
    
    # Registrar requisição atual
    client_data["minute_requests"].append(current_time)
    client_data["day_requests"].append(current_time)

def validate_api_key(
    x_api_key: Optional[str] = Header(None, alias=settings.API_KEY_HEADER)
) -> Optional[str]:
    """
    Valida API key se fornecida.
    Por enquanto, apenas registra para futuro uso.
    
    Args:
        x_api_key: API key do header
        
    Returns:
        API key validada ou None
    """
    if x_api_key:
        # TODO: Implementar validação real de API keys
        # Por enquanto, apenas aceita qualquer key
        logger.info(f"API key fornecida: {x_api_key[:8]}..." if len(x_api_key) > 8 else x_api_key)
        return x_api_key
    
    return None

def get_session_info(request: Request) -> Dict[str, Any]:
    """
    Extrai informações da sessão/cliente.
    
    Args:
        request: Request do FastAPI
        
    Returns:
        Informações do cliente
    """
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        # Gerar session ID baseado no IP e User-Agent
        import hashlib
        client_ip = get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")
        session_data = f"{client_ip}:{user_agent}:{int(time.time() / 3600)}"  # Muda a cada hora
        session_id = hashlib.md5(session_data.encode()).hexdigest()[:16]
    
    return {
        "session_id": session_id,
        "client_ip": get_client_ip(request),
        "user_agent": request.headers.get("User-Agent", ""),
        "referer": request.headers.get("Referer"),
        "request_id": getattr(request.state, "request_id", None)
    }

def check_service_availability(service_name: str) -> None:
    """
    Verifica se um serviço específico está habilitado.
    
    Args:
        service_name: Nome do serviço (ocr, barcode, qrcode)
        
    Raises:
        HTTPException: Se serviço não estiver habilitado
    """
    service_enabled = {
        "ocr": settings.ENABLE_OCR,
        "barcode": settings.ENABLE_BARCODE,
        "qrcode": settings.ENABLE_QRCODE,
        "batch": settings.ENABLE_BATCH_PROCESSING
    }
    
    if service_name not in service_enabled:
        raise HTTPException(
            status_code=400,
            detail=f"Serviço desconhecido: {service_name}"
        )
    
    if not service_enabled[service_name]:
        raise HTTPException(
            status_code=503,
            detail=f"Serviço {service_name} não está habilitado"
        )

# Dependências compostas
def get_common_deps(
    request: Request,
    db: Session = Depends(get_db),
    api_key: Optional[str] = Depends(validate_api_key)
) -> Dict[str, Any]:
    """
    Dependência composta com validações comuns.
    
    Args:
        request: Request do FastAPI
        db: Sessão do banco
        api_key: API key validada
        
    Returns:
        Dicionário com dependências comuns
    """
    # Rate limiting
    rate_limit_check(request)
    
    # Informações da sessão
    session_info = get_session_info(request)
    
    return {
        "db": db,
        "session_info": session_info,
        "api_key": api_key,
        "request": request
    }

def get_ocr_deps(
    common: Dict[str, Any] = Depends(get_common_deps)
) -> Dict[str, Any]:
    """Dependências específicas para endpoints OCR."""
    check_service_availability("ocr")
    return common

def get_barcode_deps(
    common: Dict[str, Any] = Depends(get_common_deps)
) -> Dict[str, Any]:
    """Dependências específicas para endpoints Barcode."""
    check_service_availability("barcode")
    return common

def get_qrcode_deps(
    common: Dict[str, Any] = Depends(get_common_deps)
) -> Dict[str, Any]:
    """Dependências específicas para endpoints QR Code."""
    check_service_availability("qrcode")
    return common

def get_batch_deps(
    common: Dict[str, Any] = Depends(get_common_deps)
) -> Dict[str, Any]:
    """Dependências específicas para processamento em lote."""
    check_service_availability("batch")
    return common

# Cleanup periódico do cache (função utilitária)
def cleanup_rate_limit_cache():
    """
    Remove entradas antigas do cache de rate limiting.
    Deve ser chamada periodicamente (ex: via cron job).
    """
    current_time = time.time()
    day_cutoff = current_time - (24 * 60 * 60)
    
    # Remover clientes inativos
    inactive_clients = []
    for client_ip, data in request_cache.items():
        if not data["day_requests"] or max(data["day_requests"]) < day_cutoff:
            inactive_clients.append(client_ip)
    
    for client_ip in inactive_clients:
        del request_cache[client_ip]
    
    logger.info(f"Cache de rate limiting limpo: {len(inactive_clients)} clientes removidos")