# app/crud/base.py
"""
Operações CRUD base para todos os modelos.
Implementa funcionalidades comuns de Create, Read, Update, Delete.
"""
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union, Type
from uuid import UUID
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func
from fastapi.encoders import jsonable_encoder

from app.models.database.base import BaseModel as DBBaseModel

ModelType = TypeVar("ModelType", bound=DBBaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Classe base para operações CRUD.
    Implementa operações padrão para qualquer modelo SQLAlchemy.
    """
    
    def __init__(self, model: Type[ModelType]):
        """
        Inicializa CRUD com o modelo específico.
        
        Args:
            model: Classe do modelo SQLAlchemy
        """
        self.model = model
    
    def get(self, db: Session, id: Union[UUID, str, int]) -> Optional[ModelType]:
        """
        Busca um registro por ID.
        
        Args:
            db: Sessão do banco de dados
            id: ID do registro
            
        Returns:
            Registro encontrado ou None
        """
        return db.query(self.model).filter(self.model.id == id).first()
    
    def get_multi(
        self, 
        db: Session, 
        *, 
        skip: int = 0, 
        limit: int = 100,
        order_by: str = "created_at",
        order_dir: str = "desc"
    ) -> List[ModelType]:
        """
        Busca múltiplos registros com paginação.
        
        Args:
            db: Sessão do banco de dados
            skip: Número de registros para pular
            limit: Número máximo de registros
            order_by: Campo para ordenação
            order_dir: Direção da ordenação (asc/desc)
            
        Returns:
            Lista de registros
        """
        query = db.query(self.model)
        
        # Aplicar ordenação
        if hasattr(self.model, order_by):
            order_column = getattr(self.model, order_by)
            if order_dir.lower() == "desc":
                query = query.order_by(desc(order_column))
            else:
                query = query.order_by(asc(order_column))
        
        return query.offset(skip).limit(limit).all()
    
    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        """
        Cria um novo registro.
        
        Args:
            db: Sessão do banco de dados
            obj_in: Dados para criação (schema Pydantic)
            
        Returns:
            Registro criado
        """
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def create_with_dict(self, db: Session, *, obj_in: Dict[str, Any]) -> ModelType:
        """
        Cria um novo registro a partir de dicionário.
        
        Args:
            db: Sessão do banco de dados
            obj_in: Dados para criação (dicionário)
            
        Returns:
            Registro criado
        """
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """
        Atualiza um registro existente.
        
        Args:
            db: Sessão do banco de dados
            db_obj: Registro existente
            obj_in: Dados para atualização
            
        Returns:
            Registro atualizado
        """
        obj_data = jsonable_encoder(db_obj)
        
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def delete(self, db: Session, *, id: Union[UUID, str, int]) -> Optional[ModelType]:
        """
        Remove um registro por ID.
        
        Args:
            db: Sessão do banco de dados
            id: ID do registro a ser removido
            
        Returns:
            Registro removido ou None se não encontrado
        """
        obj = db.query(self.model).get(id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj
    
    def count(self, db: Session, **filters) -> int:
        """
        Conta registros com filtros opcionais.
        
        Args:
            db: Sessão do banco de dados
            **filters: Filtros a serem aplicados
            
        Returns:
            Número de registros
        """
        query = db.query(self.model)
        
        # Aplicar filtros
        for field, value in filters.items():
            if hasattr(self.model, field) and value is not None:
                query = query.filter(getattr(self.model, field) == value)
        
        return query.count()
    
    def exists(self, db: Session, id: Union[UUID, str, int]) -> bool:
        """
        Verifica se um registro existe.
        
        Args:
            db: Sessão do banco de dados
            id: ID do registro
            
        Returns:
            True se existe, False caso contrário
        """
        return db.query(self.model).filter(self.model.id == id).first() is not None
    
    def get_by_field(
        self, 
        db: Session, 
        field_name: str, 
        field_value: Any
    ) -> Optional[ModelType]:
        """
        Busca registro por campo específico.
        
        Args:
            db: Sessão do banco de dados
            field_name: Nome do campo
            field_value: Valor do campo
            
        Returns:
            Primeiro registro encontrado ou None
        """
        if not hasattr(self.model, field_name):
            return None
        
        return db.query(self.model).filter(
            getattr(self.model, field_name) == field_value
        ).first()
    
    def get_multi_by_field(
        self, 
        db: Session, 
        field_name: str, 
        field_value: Any,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """
        Busca múltiplos registros por campo específico.
        
        Args:
            db: Sessão do banco de dados
            field_name: Nome do campo
            field_value: Valor do campo
            skip: Registros para pular
            limit: Limite de registros
            
        Returns:
            Lista de registros encontrados
        """
        if not hasattr(self.model, field_name):
            return []
        
        return db.query(self.model).filter(
            getattr(self.model, field_name) == field_value
        ).offset(skip).limit(limit).all()
    
    def search(
        self,
        db: Session,
        *,
        search_term: str,
        search_fields: List[str],
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """
        Busca registros por termo em múltiplos campos.
        
        Args:
            db: Sessão do banco de dados
            search_term: Termo de busca
            search_fields: Campos para buscar
            skip: Registros para pular
            limit: Limite de registros
            
        Returns:
            Lista de registros encontrados
        """
        query = db.query(self.model)
        
        # Criar condições OR para busca
        conditions = []
        for field in search_fields:
            if hasattr(self.model, field):
                field_attr = getattr(self.model, field)
                # Verificar se o campo é string para usar ILIKE
                if hasattr(field_attr.property, 'columns'):
                    column_type = str(field_attr.property.columns[0].type)
                    if 'VARCHAR' in column_type or 'TEXT' in column_type:
                        conditions.append(field_attr.ilike(f"%{search_term}%"))
                    else:
                        conditions.append(field_attr == search_term)
        
        if conditions:
            query = query.filter(or_(*conditions))
        
        return query.offset(skip).limit(limit).all()
    
    def filter_by_date_range(
        self,
        db: Session,
        *,
        date_field: str = "created_at",
        date_from: Optional[Any] = None,
        date_to: Optional[Any] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """
        Filtra registros por intervalo de datas.
        
        Args:
            db: Sessão do banco de dados
            date_field: Campo de data para filtrar
            date_from: Data inicial
            date_to: Data final
            skip: Registros para pular
            limit: Limite de registros
            
        Returns:
            Lista de registros no intervalo
        """
        query = db.query(self.model)
        
        if hasattr(self.model, date_field):
            date_column = getattr(self.model, date_field)
            
            if date_from:
                query = query.filter(date_column >= date_from)
            
            if date_to:
                query = query.filter(date_column <= date_to)
        
        return query.offset(skip).limit(limit).all()
    
    def bulk_create(
        self, 
        db: Session, 
        *, 
        objs_in: List[Union[CreateSchemaType, Dict[str, Any]]]
    ) -> List[ModelType]:
        """
        Cria múltiplos registros em lote.
        
        Args:
            db: Sessão do banco de dados
            objs_in: Lista de dados para criação
            
        Returns:
            Lista de registros criados
        """
        db_objs = []
        
        for obj_in in objs_in:
            if isinstance(obj_in, dict):
                obj_data = obj_in
            else:
                obj_data = jsonable_encoder(obj_in)
            
            db_obj = self.model(**obj_data)
            db_objs.append(db_obj)
        
        db.add_all(db_objs)
        db.commit()
        
        for db_obj in db_objs:
            db.refresh(db_obj)
        
        return db_objs
    
    def bulk_delete(
        self, 
        db: Session, 
        *, 
        ids: List[Union[UUID, str, int]]
    ) -> int:
        """
        Remove múltiplos registros em lote.
        
        Args:
            db: Sessão do banco de dados
            ids: Lista de IDs para remoção
            
        Returns:
            Número de registros removidos
        """
        count = db.query(self.model).filter(self.model.id.in_(ids)).count()
        db.query(self.model).filter(self.model.id.in_(ids)).delete(synchronize_session=False)
        db.commit()
        return count
    
    def get_stats(self, db: Session) -> Dict[str, Any]:
        """
        Retorna estatísticas básicas da tabela.
        
        Args:
            db: Sessão do banco de dados
            
        Returns:
            Dicionário com estatísticas
        """
        total_count = db.query(self.model).count()
        
        stats = {
            "total_records": total_count,
            "table_name": self.model.__tablename__
        }
        
        # Adicionar estatísticas de data se o modelo tem created_at
        if hasattr(self.model, 'created_at'):
            oldest = db.query(func.min(self.model.created_at)).scalar()
            newest = db.query(func.max(self.model.created_at)).scalar()
            
            stats.update({
                "oldest_record": oldest.isoformat() if oldest else None,
                "newest_record": newest.isoformat() if newest else None
            })
        
        return stats
    
    def soft_delete(self, db: Session, *, id: Union[UUID, str, int]) -> Optional[ModelType]:
        """
        Soft delete para modelos que suportam (have is_deleted field).
        
        Args:
            db: Sessão do banco de dados
            id: ID do registro
            
        Returns:
            Registro marcado como deletado ou None
        """
        obj = self.get(db, id)
        if obj and hasattr(obj, 'soft_delete'):
            obj.soft_delete()
            db.add(obj)
            db.commit()
            db.refresh(obj)
        return obj
    
    def restore(self, db: Session, *, id: Union[UUID, str, int]) -> Optional[ModelType]:
        """
        Restaura um registro soft deleted.
        
        Args:
            db: Sessão do banco de dados
            id: ID do registro
            
        Returns:
            Registro restaurado ou None
        """
        obj = self.get(db, id)
        if obj and hasattr(obj, 'restore'):
            obj.restore()
            db.add(obj)
            db.commit()
            db.refresh(obj)
        return obj