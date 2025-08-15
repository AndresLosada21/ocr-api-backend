# app/crud/ocr_result.py
"""
CRUD para resultados de OCR.
Assumindo modelo OCRResult em app/models/database/ocr_result.py.
"""
from typing import Any, Dict, Optional, List
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.database.ocr_result import OCRResult  # Assumir existência

def create_ocr_result(db: Session, result: Dict[str, Any]) -> OCRResult:
    db_result = OCRResult(**result)
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    return db_result

def get_ocr_result(db: Session, result_id: UUID) -> Optional[OCRResult]:
    return db.query(OCRResult).filter(OCRResult.id == result_id).first()

def get_ocr_results_by_job(db: Session, job_id: UUID) -> List[OCRResult]:
    return db.query(OCRResult).filter(OCRResult.job_id == job_id).all()