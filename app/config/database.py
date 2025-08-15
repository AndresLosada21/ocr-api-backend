"""
Configuração do banco de dados PostgreSQL.
Setup do SQLAlchemy com connection pooling otimizado.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Generator
import logging

from app.config.settings import settings

logger = logging.getLogger(__name__)

# Configuração do engine PostgreSQL
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,
    pool_recycle=settings.DATABASE_POOL_RECYCLE,
    pool_pre_ping=True,  # Verifica conexões antes de usar
    echo=settings.DATABASE_ECHO,  # Log SQL queries se habilitado
    future=True,  # SQLAlchemy 2.0 style
    connect_args={
        "options": "-c timezone=utc"  # Força timezone UTC
    }
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)

# Base declarativa para modelos
Base = declarative_base()

# Event listeners para melhor gerenciamento de conexões
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Configura parâmetros de conexão PostgreSQL."""
    if settings.is_development:
        logger.debug("Nova conexão estabelecida com PostgreSQL")

@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Log quando uma conexão é retirada do pool."""
    if settings.DATABASE_ECHO:
        logger.debug("Conexão retirada do pool")

@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    """Log quando uma conexão é devolvida ao pool."""
    if settings.DATABASE_ECHO:
        logger.debug("Conexão devolvida ao pool")

def get_db() -> Generator[Session, None, None]:
    """
    Dependency para injeção de sessão do banco de dados.
    Usado nos endpoints FastAPI.
    
    Yields:
        Session: Sessão do SQLAlchemy
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Erro na sessão do banco: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

def create_tables():
    """
    Cria todas as tabelas no banco de dados.
    Usado apenas para desenvolvimento/testes.
    Em produção, usar Alembic migrations.
    """
    try:
        logger.info("Criando tabelas no banco de dados...")
        Base.metadata.create_all(bind=engine)
        logger.info("Tabelas criadas com sucesso")
    except Exception as e:
        logger.error(f"Erro ao criar tabelas: {str(e)}")
        raise

def drop_tables():
    """
    Remove todas as tabelas do banco de dados.
    CUIDADO: Usado apenas para desenvolvimento/testes.
    """
    if settings.is_production:
        raise RuntimeError("drop_tables() não pode ser executado em produção!")
    
    try:
        logger.warning("Removendo todas as tabelas...")
        Base.metadata.drop_all(bind=engine)
        logger.warning("Tabelas removidas")
    except Exception as e:
        logger.error(f"Erro ao remover tabelas: {str(e)}")
        raise

def check_db_connection() -> bool:
    """
    Verifica se a conexão com o banco está funcionando.
    
    Returns:
        bool: True se conectado, False caso contrário
    """
    try:
        from sqlalchemy import text
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1 as test"))
            return result.fetchone()[0] == 1
    except Exception as e:
        logger.error(f"Erro na conexão com banco: {str(e)}")
        return False

def get_db_info() -> dict:
    """
    Retorna informações sobre o banco de dados.
    
    Returns:
        dict: Informações do banco
    """
    try:
        with engine.connect() as connection:
            # Versão do PostgreSQL
            from sqlalchemy import text
            version_result = connection.execute(text("SELECT version()"))
            version = version_result.fetchone()[0]
            
            # Estatísticas de conexão
            pool = engine.pool
            
            pool_status = {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow()
            }
            
            # Adicionar invalidated apenas se o método existir
            try:
                pool_status["invalidated"] = pool.invalidated()
            except AttributeError:
                pass
            
            return {
                "version": version,
                "pool_status": pool_status,
                "connection_url": str(engine.url).replace(engine.url.password, "*****") if engine.url.password else str(engine.url)
            }
    except Exception as e:
        logger.error(f"Erro ao obter informações do banco: {str(e)}")
        return {"error": str(e)}

class DatabaseManager:
    """
    Gerenciador de operações do banco de dados.
    Centraliza operações administrativas.
    """
    
    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal
    
    def health_check(self) -> dict:
        """
        Verificação de saúde do banco de dados.
        
        Returns:
            dict: Status da saúde do banco
        """
        try:
            start_time = time.time()
            
            with self.engine.connect() as connection:
                # Test query
                from sqlalchemy import text
                connection.execute(text("SELECT 1"))
                
                # Connection pool stats
                pool = self.engine.pool
                
                response_time = (time.time() - start_time) * 1000
                
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
                    "response_time_ms": round(response_time, 2),
                    "pool": pool_info
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def get_session(self) -> Session:
        """
        Cria uma nova sessão do banco.
        Para uso em serviços que não são endpoints.
        
        Returns:
            Session: Nova sessão do SQLAlchemy
        """
        return self.SessionLocal()
    
    def close_all_connections(self):
        """
        Fecha todas as conexões do pool.
        Usado na finalização da aplicação.
        """
        try:
            self.engine.dispose()
            logger.info("Todas as conexões do banco foram fechadas")
        except Exception as e:
            logger.error(f"Erro ao fechar conexões: {str(e)}")

# Instância global do gerenciador
db_manager = DatabaseManager()

# Função para finalização da aplicação
def close_db():
    """
    Fecha conexões do banco na finalização da aplicação.
    """
    db_manager.close_all_connections()

# Import para melhor debugging
import time