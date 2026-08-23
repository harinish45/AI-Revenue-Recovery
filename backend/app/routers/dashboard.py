"""
dashboard.py — Dashboard summary endpoint
------------------------------------------
GET /api/dashboard/summary — returns real-time metrics
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..services.metrics_service import get_metrics
from ..schemas import DashboardSummary

router = APIRouter()


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)):
    """
    Return live dashboard metrics computed from the database.

    Metrics include:
      - total_payments
      - total_at_risk (failed/abandoned payments only)
      - total_recovered
      - recovery_rate_percent
      - open_cases
      - escalated_cases
      - recovery_attempts
      - successful_recoveries
      - failed_recoveries
    """
    return get_metrics(db)
