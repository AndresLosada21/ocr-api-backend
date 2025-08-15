# app/api/routes/__init__.py
"""
Módulo de rotas da API.
Centraliza todas as rotas disponíveis.
"""

# Import todas as rotas para facilitar o uso
from . import health
from . import ocr
from . import barcode
from . import qrcode
from . import jobs

__all__ = [
    "health",
    "ocr", 
    "barcode",
    "qrcode",
    "jobs"
]