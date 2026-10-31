from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import DashboardSummary, RecoveryAnalyticsOut
from ..security.auth import require_readonly
from ..services.metrics_service import get_metrics, get_recovery_analytics

router = APIRouter(dependencies=[Depends(require_readonly)])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)):
    return get_metrics(db)


@router.get("/recovery-analytics", response_model=RecoveryAnalyticsOut)
def recovery_analytics(db: Session = Depends(get_db)):
    return get_recovery_analytics(db)
