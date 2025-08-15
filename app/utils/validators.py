# app/utils/validators.py
"""
Validadores personalizados para a API.
Validações de dados, formatos, limites e regras de negócio.
"""
import re
import ipaddress
from typing import Any, List, Dict, Optional, Union
from datetime import datetime, date
from urllib.parse import urlparse
from fastapi import UploadFile
import magic
import logging

from app.config.settings import settings
from app.utils.exceptions import ValidationError

logger = logging.getLogger(__name__)

class DataValidators:
    """Classe com validadores de dados."""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Valida formato de email.
        
        Args:
            email: String do email
            
        Returns:
            True se válido
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_phone(phone: str, country: str = "BR") -> bool:
        """
        Valida formato de telefone.
        
        Args:
            phone: String do telefone
            country: Código do país
            
        Returns:
            True se válido
        """
        # Remove caracteres não numéricos
        clean_phone = re.sub(r'[^\d]', '', phone)
        
        if country == "BR":
            # Formato brasileiro: (XX) XXXXX-XXXX ou (XX) XXXX-XXXX
            return len(clean_phone) in [10, 11] and clean_phone[:2] in [
                "11", "12", "13", "14", "15", "16", "17", "18", "19",  # SP
                "21", "22", "24",  # RJ
                "27", "28",  # ES
                "31", "32", "33", "34", "35", "37", "38",  # MG
                # Adicionar outros DDDs conforme necessário
            ]
        
        # Validação genérica
        return 7 <= len(clean_phone) <= 15
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """
        Valida formato de URL.
        
        Args:
            url: String da URL
            
        Returns:
            True se válido
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    @staticmethod
    def validate_ip_address(ip: str) -> bool:
        """
        Valida endereço IP (v4 ou v6).
        
        Args:
            ip: String do IP
            
        Returns:
            True se válido
        """
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_date_range(date_from: date, date_to: date) -> bool:
        """
        Valida intervalo de datas.
        
        Args:
            date_from: Data inicial
            date_to: Data final
            
        Returns:
            True se válido
        """
        if date_from > date_to:
            return False
        
        # Verificar se não é muito distante no futuro
        today = date.today()
        if date_to > today:
            return False
        
        # Verificar se não é muito antigo
        max_days_back = 365 * 2  # 2 anos
        if (today - date_from).days > max_days_back:
            return False
        
        return True
    
    @staticmethod
    def validate_language_code(lang_code: str) -> bool:
        """
        Valida código de idioma.
        
        Args:
            lang_code: Código do idioma
            
        Returns:
            True se válido
        """
        valid_languages = ['pt', 'en', 'es', 'fr', 'de', 'it', 'ja', 'ko', 'zh']
        return lang_code.lower() in valid_languages
    
    @staticmethod
    def validate_barcode_type(barcode_type: str) -> bool:
        """
        Valida tipo de código de barras.
        
        Args:
            barcode_type: Tipo do código
            
        Returns:
            True se válido
        """
        valid_types = [
            'EAN13', 'EAN8', 'CODE128', 'CODE39', 'CODE93',
            'CODABAR', 'ITF', 'QRCODE', 'PDF417', 'DATAMATRIX'
        ]
        return barcode_type.upper() in valid_types
    
    @staticmethod
    def validate_job_type(job_type: str) -> bool:
        """
        Valida tipo de job.
        
        Args:
            job_type: Tipo do job
            
        Returns:
            True se válido
        """
        valid_types = ['ocr', 'barcode', 'qrcode', 'all']
        return job_type.lower() in valid_types
    
    @staticmethod
    def validate_job_status(status: str) -> bool:
        """
        Valida status de job.
        
        Args:
            status: Status do job
            
        Returns:
            True se válido
        """
        valid_statuses = ['pending', 'processing', 'completed', 'failed', 'cancelled']
        return status.lower() in valid_statuses

class FileValidators:
    """Classe com validadores de arquivos."""
    
    @staticmethod
    def validate_file_size(file: UploadFile) -> bool:
        """
        Valida tamanho do arquivo.
        
        Args:
            file: Arquivo de upload
            
        Returns:
            True se válido
            
        Raises:
            ValidationError: Se arquivo muito grande
        """
        if hasattr(file, 'size') and file.size:
            file_size = file.size
        else:
            # Calcular tamanho
            file.file.seek(0, 2)
            file_size = file.file.tell()
            file.file.seek(0)
        
        if file_size > settings.max_image_size_bytes:
            raise ValidationError(
                f"Arquivo muito grande: {file_size / (1024*1024):.1f}MB "
                f"(máximo: {settings.MAX_IMAGE_SIZE_MB}MB)"
            )
        
        if file_size == 0:
            raise ValidationError("Arquivo está vazio")
        
        return True
    
    @staticmethod
    def validate_file_extension(filename: str) -> bool:
        """
        Valida extensão do arquivo.
        
        Args:
            filename: Nome do arquivo
            
        Returns:
            True se válido
            
        Raises:
            ValidationError: Se extensão não suportada
        """
        if not filename:
            raise ValidationError("Nome do arquivo não fornecido")
        
        extension = filename.split('.')[-1].lower()
        
        if extension not in settings.ALLOWED_EXTENSIONS:
            raise ValidationError(
                f"Extensão '{extension}' não suportada. "
                f"Extensões válidas: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )
        
        return True
    
    @staticmethod
    def validate_file_content(file_path: str) -> Dict[str, Any]:
        """
        Valida conteúdo do arquivo usando python-magic.
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            Dicionário com informações do arquivo
            
        Raises:
            ValidationError: Se arquivo corrompido ou tipo inválido
        """
        try:
            # Detectar tipo MIME
            mime_type = magic.from_file(file_path, mime=True)
            
            # Tipos MIME aceitos
            valid_mime_types = [
                'image/jpeg', 'image/png', 'image/gif', 'image/bmp',
                'image/tiff', 'image/webp', 'application/pdf'
            ]
            
            if mime_type not in valid_mime_types:
                raise ValidationError(f"Tipo de arquivo não suportado: {mime_type}")
            
            # Descrição do arquivo
            description = magic.from_file(file_path)
            
            return {
                "mime_type": mime_type,
                "description": description,
                "is_valid": True
            }
            
        except Exception as e:
            logger.error(f"Erro na validação de conteúdo do arquivo {file_path}: {str(e)}")
            raise ValidationError(f"Erro ao validar arquivo: {str(e)}")
    
    @staticmethod
    def validate_image_dimensions(width: int, height: int) -> bool:
        """
        Valida dimensões da imagem.
        
        Args:
            width: Largura em pixels
            height: Altura em pixels
            
        Returns:
            True se válido
            
        Raises:
            ValidationError: Se dimensões inválidas
        """
        min_dim = settings.MIN_IMAGE_DIMENSION
        max_dim = settings.MAX_IMAGE_DIMENSION
        
        if width < min_dim or height < min_dim:
            raise ValidationError(
                f"Imagem muito pequena: {width}x{height} "
                f"(mínimo: {min_dim}x{min_dim})"
            )
        
        if width > max_dim or height > max_dim:
            raise ValidationError(
                f"Imagem muito grande: {width}x{height} "
                f"(máximo: {max_dim}x{max_dim})"
            )
        
        return True

class BusinessValidators:
    """Classe com validadores de regras de negócio."""
    
    @staticmethod
    def validate_rate_limit(
        current_count: int, 
        limit: int, 
        period: str
    ) -> bool:
        """
        Valida se está dentro do rate limit.
        
        Args:
            current_count: Contagem atual
            limit: Limite permitido
            period: Período (minute, day)
            
        Returns:
            True se válido
            
        Raises:
            ValidationError: Se excedeu limite
        """
        if current_count >= limit:
            raise ValidationError(
                f"Rate limit excedido: {current_count}/{limit} por {period}"
            )
        
        return True
    
    @staticmethod
    def validate_concurrent_jobs(current_jobs: int) -> bool:
        """
        Valida número de jobs simultâneos.
        
        Args:
            current_jobs: Jobs atualmente em processamento
            
        Returns:
            True se válido
            
        Raises:
            ValidationError: Se muitos jobs simultâneos
        """
        if current_jobs >= settings.MAX_CONCURRENT_JOBS:
            raise ValidationError(
                f"Muitos jobs simultâneos: {current_jobs}/{settings.MAX_CONCURRENT_JOBS}"
            )
        
        return True
    
    @staticmethod
    def validate_batch_size(file_count: int) -> bool:
        """
        Valida tamanho do lote para processamento.
        
        Args:
            file_count: Número de arquivos no lote
            
        Returns:
            True se válido
            
        Raises:
            ValidationError: Se lote muito grande
        """
        max_batch = 50  # Limite padrão
        
        if file_count > max_batch:
            raise ValidationError(
                f"Lote muito grande: {file_count} arquivos (máximo: {max_batch})"
            )
        
        if file_count == 0:
            raise ValidationError("Lote vazio")
        
        return True
    
    @staticmethod
    def validate_processing_parameters(
        job_type: str, 
        params: Dict[str, Any]
    ) -> bool:
        """
        Valida parâmetros de processamento específicos por tipo.
        
        Args:
            job_type: Tipo do job
            params: Parâmetros fornecidos
            
        Returns:
            True se válido
            
        Raises:
            ValidationError: Se parâmetros inválidos
        """
        if job_type == "ocr":
            return BusinessValidators._validate_ocr_params(params)
        elif job_type == "barcode":
            return BusinessValidators._validate_barcode_params(params)
        elif job_type == "qrcode":
            return BusinessValidators._validate_qrcode_params(params)
        
        return True
    
    @staticmethod
    def _validate_ocr_params(params: Dict[str, Any]) -> bool:
        """Valida parâmetros específicos de OCR."""
        if 'language' in params:
            if not DataValidators.validate_language_code(params['language']):
                raise ValidationError(f"Idioma inválido: {params['language']}")
        
        if 'return_confidence' in params:
            if not isinstance(params['return_confidence'], bool):
                raise ValidationError("return_confidence deve ser boolean")
        
        return True
    
    @staticmethod
    def _validate_barcode_params(params: Dict[str, Any]) -> bool:
        """Valida parâmetros específicos de códigos de barras."""
        if 'barcode_types' in params and params['barcode_types']:
            for barcode_type in params['barcode_types']:
                if not DataValidators.validate_barcode_type(barcode_type):
                    raise ValidationError(f"Tipo de código inválido: {barcode_type}")
        
        return True
    
    @staticmethod
    def _validate_qrcode_params(params: Dict[str, Any]) -> bool:
        """Valida parâmetros específicos de QR codes."""
        if 'multiple' in params:
            if not isinstance(params['multiple'], bool):
                raise ValidationError("multiple deve ser boolean")
        
        if 'data' in params:  # Para geração de QR
            if len(params['data']) > 2000:
                raise ValidationError("Dados muito longos para QR code (máximo: 2000 caracteres)")
        
        return True

class SecurityValidators:
    """Classe com validadores de segurança."""
    
    @staticmethod
    def validate_session_id(session_id: str) -> bool:
        """
        Valida formato do session ID.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            True se válido
        """
        if not session_id:
            return False
        
        # Deve ter entre 16 e 128 caracteres alfanuméricos
        if not (16 <= len(session_id) <= 128):
            return False
        
        # Deve conter apenas caracteres seguros
        safe_chars = re.match(r'^[a-zA-Z0-9_-]+$', session_id)
        return bool(safe_chars)
    
    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """
        Valida formato da API key.
        
        Args:
            api_key: API key
            
        Returns:
            True se válido
        """
        if not api_key:
            return False
        
        # Deve ter entre 32 e 64 caracteres
        if not (32 <= len(api_key) <= 64):
            return False
        
        # Deve ser alfanumérico
        return api_key.isalnum()
    
    @staticmethod
    def validate_user_agent(user_agent: str) -> bool:
        """
        Valida User-Agent para detectar bots maliciosos.
        
        Args:
            user_agent: String do User-Agent
            
        Returns:
            True se válido
        """
        if not user_agent:
            return False
        
        # Verificar padrões suspeitos
        suspicious_patterns = [
            r'bot|crawler|spider|scraper',
            r'hack|exploit|attack',
            r'sql|script|eval|exec'
        ]
        
        ua_lower = user_agent.lower()
        for pattern in suspicious_patterns:
            if re.search(pattern, ua_lower):
                logger.warning(f"User-Agent suspeito detectado: {user_agent}")
                return False
        
        return True
    
    @staticmethod
    def validate_upload_safety(file_content: bytes) -> bool:
        """
        Valida segurança do conteúdo do arquivo.
        
        Args:
            file_content: Conteúdo binário do arquivo
            
        Returns:
            True se seguro
            
        Raises:
            ValidationError: Se arquivo perigoso
        """
        # Verificar assinaturas de arquivos executáveis
        dangerous_signatures = [
            b'MZ',  # Executável PE
            b'\x7fELF',  # Executável ELF
            b'PK',  # ZIP (pode conter executáveis)
        ]
        
        for signature in dangerous_signatures:
            if file_content.startswith(signature):
                raise ValidationError("Tipo de arquivo potencialmente perigoso detectado")
        
        # Verificar tamanho suspeito (muito pequeno ou muito grande)
        if len(file_content) < 100:
            raise ValidationError("Arquivo muito pequeno para ser uma imagem válida")
        
        return True

# Funções utilitárias
def validate_upload_file(file: UploadFile) -> Dict[str, Any]:
    """
    Executa validação completa de arquivo de upload.
    
    Args:
        file: Arquivo de upload
        
    Returns:
        Dicionário com informações de validação
    """
    # Validações básicas
    FileValidators.validate_file_size(file)
    FileValidators.validate_file_extension(file.filename)
    
    # Ler conteúdo para validações de segurança
    content = file.file.read()
    file.file.seek(0)  # Resetar posição
    
    SecurityValidators.validate_upload_safety(content)
    
    return {
        "filename": file.filename,
        "size_bytes": len(content),
        "is_valid": True,
        "validations_passed": [
            "file_size", "file_extension", "upload_safety"
        ]
    }

def validate_request_data(data: Dict[str, Any], validation_rules: Dict[str, Any]) -> bool:
    """
    Valida dados de requisição baseado em regras.
    
    Args:
        data: Dados a validar
        validation_rules: Regras de validação
        
    Returns:
        True se válido
    """
    for field, rules in validation_rules.items():
        if field in data:
            value = data[field]
            
            if 'required' in rules and rules['required'] and not value:
                raise ValidationError(f"Campo obrigatório: {field}")
            
            if 'type' in rules:
                expected_type = rules['type']
                if not isinstance(value, expected_type):
                    raise ValidationError(f"Tipo inválido para {field}: esperado {expected_type.__name__}")
            
            if 'min_length' in rules and len(str(value)) < rules['min_length']:
                raise ValidationError(f"Valor muito curto para {field}")
            
            if 'max_length' in rules and len(str(value)) > rules['max_length']:
                raise ValidationError(f"Valor muito longo para {field}")
    
    return True