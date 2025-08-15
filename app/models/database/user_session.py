# app/models/database/user_session.py
"""
Modelo para sessões de usuário e analytics.
Controla rate limiting e estatísticas de uso.
"""
from sqlalchemy import Column, String, Integer, Date, DateTime, Boolean, Float, JSON
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.sql import func
from typing import Dict, Any, Optional
from datetime import datetime, date, timezone, timedelta

from app.models.database.base import BaseModel

class UserSession(BaseModel):
    """
    Modelo para gerenciar sessões de usuário e controle de acesso.
    Usado para rate limiting, analytics e tracking de uso.
    """
    
    __tablename__ = "user_sessions"
    __table_args__ = {
        'comment': 'Sessões de usuário para analytics e rate limiting'
    }
    
    # ======================
    # IDENTIFICATION
    # ======================
    session_id = Column(
        String(128),
        unique=True,
        nullable=False,
        comment="ID único da sessão do usuário"
    )
    
    # ======================
    # CLIENT INFORMATION
    # ======================
    client_ip = Column(
        INET,
        nullable=True,
        comment="Endereço IP do cliente"
    )
    
    user_agent = Column(
        String(512),
        nullable=True,
        comment="User agent do navegador/cliente"
    )
    
    country_code = Column(
        String(2),
        nullable=True,
        comment="Código do país baseado no IP"
    )
    
    city = Column(
        String(100),
        nullable=True,
        comment="Cidade baseada no IP"
    )
    
    timezone = Column(
        String(50),
        nullable=True,
        comment="Timezone do cliente"
    )
    
    # ======================
    # USAGE STATISTICS
    # ======================
    first_seen = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Data/hora da primeira requisição"
    )
    
    last_seen = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Data/hora da última requisição"
    )
    
    total_jobs = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Total de jobs processados nesta sessão"
    )
    
    total_requests = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Total de requisições feitas"
    )
    
    # ======================
    # DAILY TRACKING
    # ======================
    jobs_today = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Jobs processados hoje"
    )
    
    requests_today = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Requisições feitas hoje"
    )
    
    last_job_date = Column(
        Date,
        server_default=func.current_date(),
        nullable=False,
        comment="Data do último job processado"
    )
    
    # ======================
    # RATE LIMITING
    # ======================
    daily_limit = Column(
        Integer,
        default=100,
        nullable=False,
        comment="Limite diário de jobs para esta sessão"
    )
    
    minute_limit = Column(
        Integer,
        default=10,
        nullable=False,
        comment="Limite por minuto para esta sessão"
    )
    
    is_blocked = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Se a sessão está bloqueada"
    )
    
    blocked_until = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data/hora até quando está bloqueada"
    )
    
    block_reason = Column(
        String(255),
        nullable=True,
        comment="Motivo do bloqueio"
    )
    
    # ======================
    # JOB TYPE STATISTICS
    # ======================
    ocr_jobs = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Total de jobs OCR"
    )
    
    barcode_jobs = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Total de jobs de códigos de barras"
    )
    
    qrcode_jobs = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Total de jobs de códigos QR"
    )
    
    batch_jobs = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Total de jobs em lote"
    )
    
    # ======================
    # PERFORMANCE METRICS
    # ======================
    avg_processing_time_ms = Column(
        Float,
        nullable=True,
        comment="Tempo médio de processamento dos jobs"
    )
    
    total_processing_time_ms = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Tempo total de processamento acumulado"
    )
    
    avg_file_size_bytes = Column(
        Integer,
        nullable=True,
        comment="Tamanho médio dos arquivos processados"
    )
    
    total_bytes_processed = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Total de bytes processados"
    )
    
    # ======================
    # SUCCESS METRICS
    # ======================
    successful_jobs = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Número de jobs bem-sucedidos"
    )
    
    failed_jobs = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Número de jobs que falharam"
    )
    
    success_rate = Column(
        Float,
        nullable=True,
        comment="Taxa de sucesso (0-1)"
    )
    
    # ======================
    # PREFERENCES
    # ======================
    preferred_language = Column(
        String(10),
        default="pt",
        nullable=False,
        comment="Idioma preferido para OCR"
    )
    
    preferred_formats = Column(
        JSON,
        nullable=True,
        comment="Formatos de arquivo mais utilizados"
    )
    
    settings_json = Column(
        JSON,
        nullable=True,
        comment="Configurações personalizadas do usuário"
    )
    
    # ======================
    # API ACCESS
    # ======================
    api_key = Column(
        String(64),
        nullable=True,
        comment="API key associada (se aplicável)"
    )
    
    api_version = Column(
        String(10),
        nullable=True,
        comment="Versão da API mais utilizada"
    )
    
    last_endpoint = Column(
        String(100),
        nullable=True,
        comment="Último endpoint acessado"
    )
    
    # ======================
    # DEVICE INFORMATION
    # ======================
    device_type = Column(
        String(20),
        nullable=True,
        comment="Tipo de dispositivo: desktop, mobile, tablet, bot"
    )
    
    browser_name = Column(
        String(50),
        nullable=True,
        comment="Nome do navegador"
    )
    
    
    os_name = Column(
        String(50),
        nullable=True,
        comment="Sistema operacional"
    )
    
    os_version = Column(
        String(20),
        nullable=True,
        comment="Versão do sistema operacional"
    )
    
    # ======================
    # METHODS
    # ======================
    
    def __init__(self, **kwargs):
        """Inicializa sessão de usuário."""
        super().__init__(**kwargs)
        self._parse_user_agent()
    
    def update_activity(self, job_type: str = None, processing_time_ms: int = None, 
                       file_size_bytes: int = None, success: bool = True) -> None:
        """
        Atualiza estatísticas de atividade da sessão.
        
        Args:
            job_type: Tipo do job (ocr, barcode, qrcode)
            processing_time_ms: Tempo de processamento
            file_size_bytes: Tamanho do arquivo
            success: Se o job foi bem-sucedido
        """
        now = datetime.now(timezone.utc)
        today = now.date()
        
        # Atualizar timestamps
        self.last_seen = now
        
        # Incrementar contadores gerais
        self.total_requests += 1
        
        if job_type:
            # Incrementar job específico
            self.total_jobs += 1
            
            if success:
                self.successful_jobs += 1
            else:
                self.failed_jobs += 1
            
            # Resetar contadores diários se mudou o dia
            if self.last_job_date != today:
                self.jobs_today = 0
                self.requests_today = 0
                self.last_job_date = today
            
            self.jobs_today += 1
            
            # Incrementar contador por tipo
            if job_type == "ocr":
                self.ocr_jobs += 1
            elif job_type == "barcode":
                self.barcode_jobs += 1
            elif job_type == "qrcode":
                self.qrcode_jobs += 1
            elif job_type == "batch":
                self.batch_jobs += 1
            
            # Atualizar métricas de performance
            if processing_time_ms:
                if self.avg_processing_time_ms:
                    # Média móvel
                    self.avg_processing_time_ms = (
                        (self.avg_processing_time_ms * (self.total_jobs - 1) + processing_time_ms) 
                        / self.total_jobs
                    )
                else:
                    self.avg_processing_time_ms = float(processing_time_ms)
                
                self.total_processing_time_ms += processing_time_ms
            
            if file_size_bytes:
                if self.avg_file_size_bytes:
                    # Média móvel
                    self.avg_file_size_bytes = int(
                        (self.avg_file_size_bytes * (self.total_jobs - 1) + file_size_bytes) 
                        / self.total_jobs
                    )
                else:
                    self.avg_file_size_bytes = file_size_bytes
                
                self.total_bytes_processed += file_size_bytes
        
        # Recalcular taxa de sucesso
        if self.total_jobs > 0:
            self.success_rate = self.successful_jobs / self.total_jobs
    
    def check_rate_limits(self) -> Dict[str, Any]:
        """
        Verifica se a sessão está dentro dos limites de rate limiting.
        
        Returns:
            Dicionário com status dos limites
        """
        now = datetime.now(timezone.utc)
        today = now.date()
        
        # Verificar se está bloqueada
        if self.is_blocked and self.blocked_until and now < self.blocked_until:
            return {
                "allowed": False,
                "reason": "session_blocked",
                "blocked_until": self.blocked_until.isoformat(),
                "block_reason": self.block_reason
            }
        
        # Verificar limite diário
        daily_count = self.jobs_today if self.last_job_date == today else 0
        if daily_count >= self.daily_limit:
            return {
                "allowed": False,
                "reason": "daily_limit_exceeded",
                "current_count": daily_count,
                "limit": self.daily_limit,
                "reset_time": "midnight"
            }
        
        return {
            "allowed": True,
            "daily_remaining": self.daily_limit - daily_count,
            "daily_used": daily_count
        }
    
    def block_session(self, reason: str, duration_hours: int = 24) -> None:
        """
        Bloqueia a sessão por um período.
        
        Args:
            reason: Motivo do bloqueio
            duration_hours: Duração do bloqueio em horas
        """
        
        self.is_blocked = True
        self.blocked_until = datetime.now(timezone.utc) + timedelta(hours=duration_hours)
        self.block_reason = reason
    
    def unblock_session(self) -> None:
        """Remove o bloqueio da sessão."""
        self.is_blocked = False
        self.blocked_until = None
        self.block_reason = None
    
    def update_preferences(self, language: str = None, formats: list = None, 
                          settings: dict = None) -> None:
        """
        Atualiza preferências do usuário.
        
        Args:
            language: Idioma preferido
            formats: Formatos mais utilizados
            settings: Configurações personalizadas
        """
        if language:
            self.preferred_language = language
        
        if formats:
            self.preferred_formats = formats
        
        if settings:
            if self.settings_json:
                self.settings_json.update(settings)
            else:
                self.settings_json = settings
    
    def _parse_user_agent(self) -> None:
        """Extrai informações do User-Agent."""
        if not self.user_agent:
            return
        
        ua = self.user_agent.lower()
        
        # Detectar tipo de dispositivo
        if any(x in ua for x in ['mobile', 'android', 'iphone']):
            self.device_type = "mobile"
        elif 'tablet' in ua or 'ipad' in ua:
            self.device_type = "tablet"
        elif any(x in ua for x in ['bot', 'crawler', 'spider', 'scraper']):
            self.device_type = "bot"
        else:
            self.device_type = "desktop"
        
        # Detectar navegador
        if 'chrome' in ua:
            self.browser_name = "Chrome"
        elif 'firefox' in ua:
            self.browser_name = "Firefox"
        elif 'safari' in ua and 'chrome' not in ua:
            self.browser_name = "Safari"
        elif 'edge' in ua:
            self.browser_name = "Edge"
        elif 'opera' in ua:
            self.browser_name = "Opera"
        else:
            self.browser_name = "Unknown"
        
        # Detectar OS
        if 'windows' in ua:
            self.os_name = "Windows"
        elif 'mac' in ua:
            self.os_name = "macOS"
        elif 'linux' in ua:
            self.os_name = "Linux"
        elif 'android' in ua:
            self.os_name = "Android"
        elif 'ios' in ua or 'iphone' in ua:
            self.os_name = "iOS"
        else:
            self.os_name = "Unknown"
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """
        Retorna resumo de uso da sessão.
        
        Returns:
            Dicionário com estatísticas de uso
        """
        return {
            "session_id": self.session_id,
            "activity": {
                "first_seen": self.first_seen.isoformat(),
                "last_seen": self.last_seen.isoformat(),
                "total_jobs": self.total_jobs,
                "total_requests": self.total_requests,
                "jobs_today": self.jobs_today,
                "success_rate": self.success_rate
            },
            "job_breakdown": {
                "ocr": self.ocr_jobs,
                "barcode": self.barcode_jobs,
                "qrcode": self.qrcode_jobs,
                "batch": self.batch_jobs
            },
            "performance": {
                "avg_processing_time_ms": self.avg_processing_time_ms,
                "total_processing_time_ms": self.total_processing_time_ms,
                "avg_file_size_bytes": self.avg_file_size_bytes,
                "total_bytes_processed": self.total_bytes_processed
            },
            "limits": {
                "daily_limit": self.daily_limit,
                "minute_limit": self.minute_limit,
                "is_blocked": self.is_blocked,
                "blocked_until": self.blocked_until.isoformat() if self.blocked_until else None
            },
            "client_info": {
                "ip": str(self.client_ip) if self.client_ip else None,
                "country": self.country_code,
                "city": self.city,
                "device_type": self.device_type,
                "browser": self.browser_name,
                "os": self.os_name
            },
            "preferences": {
                "language": self.preferred_language,
                "formats": self.preferred_formats,
                "timezone": self.timezone
            }
        }
    
    def is_active_today(self) -> bool:
        """Verifica se a sessão teve atividade hoje."""
        return self.last_job_date == date.today()
    
    def days_since_last_activity(self) -> int:
        """Retorna número de dias desde a última atividade."""
        return (date.today() - self.last_job_date).days
    
    def get_efficiency_score(self) -> float:
        """
        Calcula score de eficiência baseado na taxa de sucesso e uso.
        
        Returns:
            Score de 0 a 1
        """
        if self.total_jobs == 0:
            return 0.0
        
        # Fatores: taxa de sucesso, frequência de uso, variedade de jobs
        success_factor = self.success_rate or 0.0
        usage_factor = min(1.0, self.total_jobs / 100)  # Normalizar por 100 jobs
        
        job_types_used = sum([
            1 if self.ocr_jobs > 0 else 0,
            1 if self.barcode_jobs > 0 else 0,
            1 if self.qrcode_jobs > 0 else 0
        ])
        variety_factor = job_types_used / 3.0
        
        return (success_factor * 0.5 + usage_factor * 0.3 + variety_factor * 0.2)
    
    @classmethod
    def create_from_request(cls, session_id: str, client_ip: str, 
                           user_agent: str, **kwargs):
        """
        Cria nova sessão a partir de dados da requisição.
        
        Args:
            session_id: ID da sessão
            client_ip: IP do cliente
            user_agent: User agent
            **kwargs: Outros parâmetros
            
        Returns:
            Nova instância de UserSession
        """
        return cls(
            session_id=session_id,
            client_ip=client_ip,
            user_agent=user_agent,
            **kwargs
        )
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """
        Converte para dicionário com opção de incluir dados sensíveis.
        
        Args:
            include_sensitive: Se deve incluir dados sensíveis (IP, user agent)
            
        Returns:
            Dicionário com dados da sessão
        """
        exclude_fields = set()
        if not include_sensitive:
            exclude_fields.update(["client_ip", "user_agent", "api_key"])
        
        return super().to_dict(exclude_fields=exclude_fields)
    
    def __repr__(self) -> str:
        """Representação string da sessão."""
        return f"<UserSession(id={self.session_id}, jobs={self.total_jobs}, active={self.is_active_today()})>"