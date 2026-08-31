from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..middleware.rate_limit import limiter
from ..schemas import BatchResponse
from ..security.auth import require_operator
from ..services.batch_executor import run_batch_recovery

router = APIRouter(dependencies=[Depends(require_operator)])


@router.post("/process", response_model=BatchResponse)
@limiter.limit(settings.RATE_LIMIT_DEMO)
def process_batch(request: Request, db: Session = Depends(get_db)):
    return run_batch_recovery(db)
