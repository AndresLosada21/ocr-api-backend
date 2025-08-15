# alembic/env.py
"""
Configuração do Alembic para migrations do banco de dados.
Integra com SQLAlchemy e configurações da aplicação.
"""
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path para imports
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

# Importar configurações da aplicação
from app.config.settings import settings
from app.config.database import Base

# Importar todos os modelos para que sejam detectados pelo Alembic
from app.models.database.processing_job import ProcessingJob
from app.models.database.base import BaseModel

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def get_database_url():
    """
    Retorna a URL do banco de dados a partir das configurações.
    Prioriza variável de ambiente, depois settings.
    """
    # Verificar variável de ambiente primeiro
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url
    
    # Fallback para configurações da aplicação
    return settings.DATABASE_URL

def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    
    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.
    
    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    
    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Configurar a URL do banco
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_database_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            include_schemas=True,
            # Configurações específicas para PostgreSQL
            render_as_batch=False,
            transaction_per_migration=True,
        )

        with context.begin_transaction():
            context.run_migrations()

# Determinar se estamos executando em modo offline ou online
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()