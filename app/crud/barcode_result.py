# app/crud/barcode_result.py
"""
CRUD para resultados de barcode.
Assumindo modelo BarcodeResult em app/models/database/barcode_result.py.
"""
from typing import Any, Dict, Optional, List
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.database.barcode_result import BarcodeResult  # Assumir existência

def create_barcode_result(db: Session, result: Dict[str, Any]) -> BarcodeResult:
    db_result = BarcodeResult(**result)
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    return db_result

def get_barcode_result(db: Session, result_id: UUID) -> Optional[BarcodeResult]:
    return db.query(BarcodeResult).filter(BarcodeResult.id == result_id).first()

def get_results_by_job(db: Session, job_id: UUID) -> List[BarcodeResult]:
    return db.query(BarcodeResult).filter(BarcodeResult.job_id == job_id).all()