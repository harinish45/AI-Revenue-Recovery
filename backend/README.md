# RecoverAI Backend

Autonomous Revenue Recovery Agent API built with FastAPI. package.json contains
only optional helper scripts; the application itself is Python/FastAPI.

## Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload

The canonical contract is maintained in ../docs/api-contract.md. Simulated
Razorpay Test Mode is the safe default. Optional model diagnosis, webhook
signature validation, and real Test Mode provider calls are disabled until
explicitly configured.
```

## API Documentation
Visit `http://localhost:8000/docs` after starting the server.
