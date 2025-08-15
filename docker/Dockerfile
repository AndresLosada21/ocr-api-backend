# Use Python 3.10 slim como base
FROM python:3.10-slim

# Definir variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    # Dependências básicas
    curl \
    wget \
    git \
    build-essential \
    pkg-config \
    # Dependências OpenCV
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgtk-3-0 \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 \
    # Dependências de imagem
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libwebp-dev \
    libopenjp2-7-dev \
    # Dependências Barcode/QR
    zbar-tools \
    libzbar0 \
    libzbar-dev \
    # Dependências PostgreSQL
    libpq-dev \
    # Limpeza
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Criar usuário não-root
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Definir diretório de trabalho
WORKDIR /app

# Criar diretórios necessários
RUN mkdir -p /app/logs /app/models /app/temp /tmp/ocr_uploads /home/appuser/.paddleocr && \
    chown -R appuser:appuser /app /tmp/ocr_uploads /home/appuser

# Copiar requirements primeiro (para melhor cache do Docker)
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Configurar permissões
RUN chown -R appuser:appuser /app

# Mudar para usuário não-root
USER appuser

# Expor porta
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando de inicialização
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]