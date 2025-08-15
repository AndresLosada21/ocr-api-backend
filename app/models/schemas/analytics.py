# app/models/schemas/analytics.py
"""
Schemas Pydantic para analytics.
"""
from pydantic import BaseModel
from typing import Dict, Optional

class AnalyticsSummary(BaseModel):
    total_jobs: int
    successful: int
    failed: int
    success_rate: float
    avg_processing_time_ms: float

class UsageByType(BaseModel):
    ocr: Optional[int] = 0
    barcode: Optional[int] = 0
    qrcode: Optional[int] = 0

class ErrorStats(BaseModel):
    errors: Dict[str, int]