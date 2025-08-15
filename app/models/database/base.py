"""
Modelo base para todos os modelos do banco de dados.
Define funcionalidades comuns e mixins.
"""
from sqlalchemy import Column, DateTime, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.sql import func
from uuid import uuid4
from datetime import datetime, timezone
from typing import Any, Dict

from app.config.database import Base

class TimestampMixin:
    """
    Mixin para campos de timestamp automáticos.
    Adiciona created_at e updated_at a qualquer modelo.
    """
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Data e hora de criação do registro"
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Data e hora da última atualização"
    )

class UUIDMixin:
    """
    Mixin para chave primária UUID.
    Gera automaticamente UUIDs para IDs.
    """
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False,
        comment="Identificador único UUID"
    )

class SoftDeleteMixin:
    """
    Mixin para soft delete.
    Permite "deletar" registros sem removê-los fisicamente.
    """
    
    is_deleted = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Flag para soft delete"
    )
    
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data e hora da deleção lógica"
    )
    
    def soft_delete(self):
        """Marca o registro como deletado."""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
    
    def restore(self):
        """Restaura um registro deletado logicamente."""
        self.is_deleted = False
        self.deleted_at = None

class AuditMixin:
    """
    Mixin para auditoria.
    Registra quem criou e modificou os registros.
    """
    
    created_by = Column(
        String(128),
        nullable=True,
        comment="ID do usuário que criou o registro"
    )
    
    updated_by = Column(
        String(128),
        nullable=True,
        comment="ID do usuário que fez a última atualização"
    )

class BaseModel(Base, UUIDMixin, TimestampMixin):
    """
    Modelo base para todas as entidades.
    Inclui UUID, timestamps e métodos utilitários.
    """
    
    __abstract__ = True
    
    def to_dict(self, exclude_fields: set = None) -> Dict[str, Any]:
        """
        Converte o modelo para dicionário.
        
        Args:
            exclude_fields: Campos a serem excluídos
            
        Returns:
            Dict com os dados do modelo
        """
        exclude_fields = exclude_fields or set()
        
        result = {}
        for column in self.__table__.columns:
            if column.name not in exclude_fields:
                value = getattr(self, column.name)
                
                # Converter tipos especiais para serialização
                if isinstance(value, datetime):
                    result[column.name] = value.isoformat()
                elif hasattr(value, '__dict__'):
                    result[column.name] = str(value)
                else:
                    result[column.name] = value
        
        return result
    
    def update_from_dict(self, data: Dict[str, Any], exclude_fields: set = None):
        """
        Atualiza o modelo a partir de um dicionário.
        
        Args:
            data: Dados para atualização
            exclude_fields: Campos a serem ignorados
        """
        exclude_fields = exclude_fields or {'id', 'created_at', 'updated_at'}
        
        for key, value in data.items():
            if key not in exclude_fields and hasattr(self, key):
                setattr(self, key, value)
    
    @classmethod
    def get_table_name(cls) -> str:
        """Retorna o nome da tabela."""
        return cls.__tablename__
    
    @classmethod
    def get_columns(cls) -> list:
        """Retorna lista de colunas da tabela."""
        return [column.name for column in cls.__table__.columns]
    
    def __repr__(self) -> str:
        """Representação string do modelo."""
        return f"<{self.__class__.__name__}(id={self.id})>"

class LogMixin:
    """
    Mixin para campos de log e debug.
    Útil para tabelas que precisam de informações extras de debug.
    """
    
    debug_info = Column(
        String,
        nullable=True,
        comment="Informações de debug em formato JSON"
    )
    
    processing_notes = Column(
        String,
        nullable=True,
        comment="Notas sobre o processamento"
    )

# Enums customizados para o banco
from enum import Enum as PyEnum
from sqlalchemy import Enum

class JobType(PyEnum):
    """Tipos de job de processamento."""
    OCR = "ocr"
    BARCODE = "barcode"
    QRCODE = "qrcode"
    ALL = "all"  # Processamento combinado

class JobStatus(PyEnum):
    """Status de job de processamento."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

# Tipos SQL personalizados
JobTypeSQL = Enum(JobType, name="job_type", values_callable=lambda obj: [e.value for e in obj])
JobStatusSQL = Enum(JobStatus, name="job_status", values_callable=lambda obj: [e.value for e in obj])