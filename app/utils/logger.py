# Path: app/utils/logger.py
"""
Sistema de logging estruturado para a aplicação.
Configuração centralizada de logs em formato de texto ou JSON.
"""
import logging
import json
import sys
import inspect
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pathlib import Path

# --- Classes de Formatação ---

class JSONFormatter(logging.Formatter):
    """Formatter personalizado para logs em JSON estruturado."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Formata o log em JSON."""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Lista de campos extras que podem ser passados para o logger
        extra_fields = [
            "request_id", "job_id", "duration_ms", "client_ip", "operation",
            "status_code", "method", "path", "user_agent", "error",
            "metric_name", "metric_value", "metric_unit", "context",
            "input_filename", "size_bytes", "language", "barcode_types", "process_time"
        ]
        
        for field in extra_fields:
            if hasattr(record, field):
                log_entry[field] = getattr(record, field)
        
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False, default=str)

class TextFormatter(logging.Formatter):
    """Formatter para logs em texto simples e colorido."""
    
    COLORS = {
        logging.DEBUG: "\033[94m",    # Azul
        logging.INFO: "\033[92m",     # Verde
        logging.WARNING: "\033[93m",  # Amarelo
        logging.ERROR: "\033[91m",    # Vermelho
        logging.CRITICAL: "\033[95m", # Magenta
    }
    RESET = "\033[0m"

    def __init__(self):
        super().__init__(
            fmt='%(asctime)s - %(name)s - %(levelname)-8s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    def format(self, record):
        log_fmt = self.COLORS.get(record.levelno, "") + self._fmt + self.RESET
        formatter = logging.Formatter(log_fmt, self.datefmt)
        return formatter.format(record)


# --- Função Principal de Configuração ---

def setup_logging():
    """
    Configura o sistema de logging para toda a aplicação.
    Esta função deve ser chamada uma única vez, no início da aplicação.
    """
    # Importar settings aqui para evitar importação circular na inicialização
    from app.config.settings import settings
    
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Configurar o logger raiz. Todos os outros loggers herdarão essa configuração.
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Limpar handlers existentes para evitar duplicação em ambientes de dev (reload)
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Escolher o formatador com base nas configurações
    formatter = JSONFormatter() if settings.LOG_FORMAT.lower() == "json" else TextFormatter()

    # Handler para o console (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Handler para o arquivo (se configurado)
    if settings.LOG_FILE_PATH:
        try:
            log_path = Path(settings.LOG_FILE_PATH)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Arquivos de log são sempre em JSON para facilitar a análise posterior
            file_handler = logging.FileHandler(log_path, encoding='utf-8')
            file_handler.setFormatter(JSONFormatter())
            root_logger.addHandler(file_handler)
        except Exception as e:
            root_logger.error(f"Falha ao configurar o log em arquivo: {e}", exc_info=True)

    # Silenciar loggers de bibliotecas muito "falantes"
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("paddleocr").setLevel(logging.ERROR)
    
    # Retornar o logger da aplicação
    return logging.getLogger("app")


# --- Funções Utilitárias de Logging ---

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Retorna uma instância de logger.
    Se o nome não for fornecido, infere o nome do módulo que a chamou.
    """
    if name is None:
        # Pega o nome do módulo que chamou esta função
        frame = inspect.currentframe().f_back
        name = frame.f_globals.get('__name__', 'unknown')
    return logging.getLogger(name)

def log_job_start(logger: logging.Logger, job_id: str, job_type: str, **kwargs):
    """Log padronizado para início de job."""
    logger.info(
        f"Iniciando job {job_type}",
        extra={'job_id': job_id, 'job_type': job_type, 'operation': 'job_start', **kwargs}
    )

def log_job_completion(logger: logging.Logger, job_id: str, duration_ms: float, success: bool, **kwargs):
    """Log padronizado para conclusão de job."""
    status = "concluído com sucesso" if success else "falhou"
    level = logging.INFO if success else logging.WARNING
    logger.log(
        level,
        f"Job {job_id} {status} em {duration_ms:.2f}ms.",
        extra={'job_id': job_id, 'duration_ms': duration_ms, 'success': success, 'operation': 'job_completion', **kwargs}
    )

def log_error(logger: logging.Logger, error: Exception, context: Optional[Dict[str, Any]] = None, **kwargs):
    """Log padronizado para erros, com traceback."""
    logger.error(
        f"Erro: {str(error)}",
        exc_info=True,
        extra={'error_type': type(error).__name__, 'context': context or {}, 'operation': 'error', **kwargs}
    )