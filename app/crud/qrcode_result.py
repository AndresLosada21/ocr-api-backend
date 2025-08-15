# app/crud/qrcode_result.py
"""
CRUD para resultados de QR Code.
Assumindo modelo QRCodeResult em app/models/database/qrcode_result.py.
"""
from typing import Any, Dict, Optional, List
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.database.qrcode_result import QRCodeResult  # Assumir existência

def create_qrcode_result(db: Session, result: Dict[str, Any]) -> QRCodeResult:
    db_result = QRCodeResult(**result)
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    return db_result

def get_qrcode_result(db: Session, result_id: UUID) -> Optional[QRCodeResult]:
    return db.query(QRCodeResult).filter(QRCodeResult.id == result_id).first()

def get_qrcode_results_by_job(db: Session, job_id: UUID) -> List[QRCodeResult]:
    return db.query(QRCodeResult).filter(QRCodeResult.job_id == job_id).all()