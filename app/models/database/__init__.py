"""Modelos do banco de dados SQLAlchemy."""

# Import all models to ensure they are registered with SQLAlchemy
from .base import BaseModel, JobType, JobStatus, JobTypeSQL, JobStatusSQL, LogMixin
from .processing_job import ProcessingJob
from .ocr_result import OCRResult
from .barcode_result import BarcodeResult
from .qrcode_result import QRCodeResult
from .user_session import UserSession

__all__ = [
    "BaseModel",
    "JobType", 
    "JobStatus",
    "JobTypeSQL",
    "JobStatusSQL", 
    "LogMixin",
    "ProcessingJob",
    "OCRResult",
    "BarcodeResult", 
    "QRCodeResult",
    "UserSession"
]