# app/utils/file_handler.py
"""
Utilitários para manipulação de arquivos e uploads.
Validação, salvamento e limpeza de arquivos temporários.
"""
import os
import hashlib
import magic
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from fastapi import UploadFile
from PIL import Image
import logging

from app.config.settings import settings
from app.utils.exceptions import (
    ValidationError, InvalidImageFormat, ImageTooLarge, 
    CorruptedImage, ProcessingError
)

logger = logging.getLogger(__name__)

class FileHandler:
    """Classe para manipulação de arquivos de upload."""
    
# app/utils/file_handler.py
"""
Utilitários para manipulação de arquivos e uploads.
Validação, salvamento e limpeza de arquivos temporários.
"""
import os
import hashlib
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from fastapi import UploadFile
from PIL import Image
import logging
from uuid import uuid4

from app.config.settings import settings
from app.utils.exceptions import (
    ValidationError, InvalidImageFormat, ImageTooLarge, 
    CorruptedImage, ProcessingError
)

logger = logging.getLogger(__name__)

class FileHandler:
    """Classe para manipulação de arquivos de upload."""
    
    def __init__(self):
        """Inicializa o handler de arquivos."""
        self.temp_dir = Path(settings.TEMP_UPLOAD_DIR)
        self.max_size = settings.max_image_size_bytes
        self.allowed_extensions = settings.ALLOWED_EXTENSIONS
        
        # Criar diretório temporário se não existir
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def validate_file(self, file: UploadFile) -> Dict[str, Any]:
        """
        Valida um arquivo de upload.
        
        Args:
            file: Arquivo enviado via FastAPI
            
        Returns:
            Dicionário com informações de validação
            
        Raises:
            ValidationError: Se arquivo inválido
        """
        if not file.filename:
            raise ValidationError("Nenhum arquivo foi enviado")
        
        # Verificar extensão
        file_ext = self._get_file_extension(file.filename)
        if file_ext not in self.allowed_extensions:
            raise InvalidImageFormat(file_ext, self.allowed_extensions)
        
        # Verificar tamanho do arquivo
        file.file.seek(0, 2)  # Ir para o final
        file_size = file.file.tell()
        file.file.seek(0)  # Voltar ao início
        
        if file_size > self.max_size:
            raise ImageTooLarge(file_size, self.max_size)
        
        if file_size == 0:
            raise ValidationError("Arquivo está vazio")
        
        return {
            "filename": file.filename,
            "extension": file_ext,
            "size_bytes": file_size,
            "content_type": file.content_type
        }
    
    def save_upload_file(self, file: UploadFile) -> Tuple[str, Dict[str, Any]]:
        """
        Salva arquivo de upload em diretório temporário.
        
        Args:
            file: Arquivo de upload
            
        Returns:
            Tupla com (caminho_arquivo, metadados)
        """
        # Validar arquivo
        file_info = self.validate_file(file)
        
        # Gerar nome único
        unique_name = f"{uuid4()}.{file_info['extension']}"
        file_path = self.temp_dir / unique_name
        
        try:
            # Salvar arquivo
            with open(file_path, "wb") as temp_file:
                shutil.copyfileobj(file.file, temp_file)
            
            # Validar integridade da imagem
            image_info = self._validate_image_integrity(file_path)
            file_info.update(image_info)
            
            # Calcular hash
            file_hash = self._calculate_file_hash(file_path)
            file_info["hash"] = file_hash
            
            logger.info(f"Arquivo salvo: {unique_name}", extra={
                "original_filename": file.filename,
                "size_bytes": file_info["size_bytes"],
                "temp_path": str(file_path)
            })
            
            return str(file_path), file_info
            
        except Exception as e:
            # Limpar arquivo em caso de erro
            if file_path.exists():
                file_path.unlink()
            
            logger.error(f"Erro ao salvar arquivo: {str(e)}")
            raise ProcessingError(f"Erro ao salvar arquivo: {str(e)}")
    
    def save_from_url(self, url: str, content: bytes) -> Tuple[str, Dict[str, Any]]:
        """
        Salva conteúdo baixado de URL.
        
        Args:
            url: URL original
            content: Conteúdo binário
            
        Returns:
            Tupla com (caminho_arquivo, metadados)
        """
        # Verificar tamanho
        if len(content) > self.max_size:
            raise ImageTooLarge(len(content), self.max_size)
        
        # Tentar detectar extensão pelo conteúdo
        extension = self._detect_image_format(content)
        if extension not in self.allowed_extensions:
            raise InvalidImageFormat(extension, self.allowed_extensions)
        
        # Gerar nome único
        unique_name = f"{uuid4()}.{extension}"
        file_path = self.temp_dir / unique_name
        
        try:
            # Salvar arquivo
            with open(file_path, "wb") as temp_file:
                temp_file.write(content)
            
            # Validar integridade
            image_info = self._validate_image_integrity(file_path)
            
            file_info = {
                "filename": url.split("/")[-1] or "image_from_url",
                "extension": extension,
                "size_bytes": len(content),
                "source_url": url,
                "hash": self._calculate_file_hash(file_path),
                **image_info
            }
            
            logger.info(f"Arquivo de URL salvo: {unique_name}", extra={
                "source_url": url,
                "size_bytes": len(content)
            })
            
            return str(file_path), file_info
            
        except Exception as e:
            # Limpar arquivo em caso de erro
            if file_path.exists():
                file_path.unlink()
            
            logger.error(f"Erro ao salvar arquivo de URL: {str(e)}")
            raise ProcessingError(f"Erro ao salvar arquivo de URL: {str(e)}")
    
    def cleanup_file(self, file_path: str) -> None:
        """
        Remove arquivo temporário.
        
        Args:
            file_path: Caminho do arquivo a ser removido
        """
        if not settings.CLEANUP_TEMP_FILES:
            return
        
        try:
            path = Path(file_path)
            if path.exists() and path.parent == self.temp_dir:
                path.unlink()
                logger.debug(f"Arquivo removido: {file_path}")
        except Exception as e:
            logger.warning(f"Erro ao remover arquivo {file_path}: {str(e)}")
    
    def cleanup_old_files(self, max_age_hours: int = 24) -> int:
        """
        Remove arquivos temporários antigos.
        
        Args:
            max_age_hours: Idade máxima em horas
            
        Returns:
            Número de arquivos removidos
        """
        import time
        
        removed_count = 0
        cutoff_time = time.time() - (max_age_hours * 3600)
        
        try:
            for file_path in self.temp_dir.iterdir():
                if file_path.is_file():
                    if file_path.stat().st_mtime < cutoff_time:
                        file_path.unlink()
                        removed_count += 1
            
            logger.info(f"Limpeza de arquivos antigos: {removed_count} arquivos removidos")
            
        except Exception as e:
            logger.error(f"Erro na limpeza de arquivos antigos: {str(e)}")
        
        return removed_count
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Retorna informações detalhadas de um arquivo.
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            Dicionário com informações do arquivo
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
        
        try:
            # Informações básicas
            stat = path.stat()
            file_info = {
                "path": str(path),
                "filename": path.name,
                "extension": path.suffix.lower().lstrip('.'),
                "size_bytes": stat.st_size,
                "created_at": stat.st_ctime,
                "modified_at": stat.st_mtime,
                "hash": self._calculate_file_hash(file_path)
            }
            
            # Informações da imagem
            if self._is_image_file(file_path):
                image_info = self._get_image_info(file_path)
                file_info.update(image_info)
            
            return file_info
            
        except Exception as e:
            logger.error(f"Erro ao obter informações do arquivo {file_path}: {str(e)}")
            raise ProcessingError(f"Erro ao analisar arquivo: {str(e)}")
    
    def _get_file_extension(self, filename: str) -> str:
        """Extrai extensão do arquivo."""
        return Path(filename).suffix.lower().lstrip('.')
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calcula hash SHA256 do arquivo."""
        hash_sha256 = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        
        return hash_sha256.hexdigest()
    
    def _detect_image_format(self, content: bytes) -> str:
        """Detecta formato da imagem pelo conteúdo."""
        # Verificar assinaturas de arquivo
        if content.startswith(b'\xff\xd8\xff'):
            return 'jpg'
        elif content.startswith(b'\x89PNG\r\n\x1a\n'):
            return 'png'
        elif content.startswith(b'GIF87a') or content.startswith(b'GIF89a'):
            return 'gif'
        elif content.startswith(b'RIFF') and b'WEBP' in content[:12]:
            return 'webp'
        elif content.startswith(b'BM'):
            return 'bmp'
        elif content.startswith(b'%PDF'):
            return 'pdf'
        else:
            # Tentar com PIL como fallback
            try:
                import io
                with Image.open(io.BytesIO(content)) as img:
                    return img.format.lower()
            except Exception:
                return 'unknown'
    
    def _validate_image_integrity(self, file_path: str) -> Dict[str, Any]:
        """
        Valida integridade da imagem e retorna informações.
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            Informações da imagem
            
        Raises:
            CorruptedImage: Se imagem corrompida
        """
        try:
            with Image.open(file_path) as img:
                # Tentar carregar a imagem para verificar integridade
                img.verify()
            
            # Reabrir para obter informações (verify() consome a imagem)
            with Image.open(file_path) as img:
                width, height = img.size
                format_name = img.format
                mode = img.mode
                
                # Verificar dimensões
                if width < settings.MIN_IMAGE_DIMENSION or height < settings.MIN_IMAGE_DIMENSION:
                    from app.utils.exceptions import ImageTooSmall
                    raise ImageTooSmall(width, height, settings.MIN_IMAGE_DIMENSION)
                
                if width > settings.MAX_IMAGE_DIMENSION or height > settings.MAX_IMAGE_DIMENSION:
                    raise ValidationError(f"Imagem muito grande: {width}x{height}")
                
                return {
                    "dimensions": {"width": width, "height": height},
                    "format": format_name,
                    "mode": mode,
                    "aspect_ratio": round(width / height, 2) if height > 0 else 0
                }
                
        except Exception as e:
            logger.error(f"Erro na validação da imagem {file_path}: {str(e)}")
            raise CorruptedImage(str(e))
    
    def _is_image_file(self, file_path: str) -> bool:
        """Verifica se é um arquivo de imagem."""
        try:
            with Image.open(file_path) as img:
                img.verify()
            return True
        except Exception:
            return False
    
    def _get_image_info(self, file_path: str) -> Dict[str, Any]:
        """Retorna informações detalhadas da imagem."""
        try:
            with Image.open(file_path) as img:
                info = {
                    "dimensions": {"width": img.width, "height": img.height},
                    "format": img.format,
                    "mode": img.mode,
                    "has_transparency": img.mode in ('RGBA', 'LA') or 'transparency' in img.info
                }
                
                # Informações EXIF se disponível
                if hasattr(img, '_getexif') and img._getexif():
                    info["has_exif"] = True
                else:
                    info["has_exif"] = False
                
                return info
                
        except Exception as e:
            logger.warning(f"Erro ao obter informações da imagem {file_path}: {str(e)}")
            return {}

# Instância global do file handler
file_handler = FileHandler()

# Funções utilitárias
def save_upload_file(file: UploadFile) -> Tuple[str, Dict[str, Any]]:
    """Função conveniente para salvar arquivo de upload."""
    return file_handler.save_upload_file(file)

def save_file_from_url(url: str, content: bytes) -> Tuple[str, Dict[str, Any]]:
    """Função conveniente para salvar arquivo de URL."""
    return file_handler.save_from_url(url, content)

def cleanup_temp_file(file_path: str) -> None:
    """Função conveniente para limpar arquivo temporário."""
    file_handler.cleanup_file(file_path)

def get_file_info(file_path: str) -> Dict[str, Any]:
    """Função conveniente para obter informações de arquivo."""
    return file_handler.get_file_info(file_path)

def cleanup_old_temp_files(max_age_hours: int = 24) -> int:
    """Função conveniente para limpeza de arquivos antigos."""
    return file_handler.cleanup_old_files(max_age_hours)