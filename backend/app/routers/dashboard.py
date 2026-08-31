from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import DashboardSummary
from ..security.auth import require_readonly
from ..services.metrics_service import get_metrics

router = APIRouter(dependencies=[Depends(require_readonly)])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)):
    return get_metrics(db)
