# RecoverAI Backend

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/harinish45/AI-Revenue-Recovery.git
   cd AI-Revenue-Recovery/backend
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables (optional, defaults work for demo):
   Create a `.env` file in the `backend` directory:
   ```env
   RAZORPAY_KEY_ID=your_test_key_id
   RAZORPAY_KEY_SECRET=your_test_key_secret
   ```

## Running the Server

```bash
uvicorn app.main:app --reload
```
The API will be available at `http://localhost:8000`.
API Documentation (Swagger UI) will be at `http://localhost:8000/docs`.

## Running Tests

```bash
pytest
```

## Demo Workflow

1. Seed data: `POST /api/demo/seed`
2. Process batch: `POST /api/batch/process`
3. Check dashboard: `GET /api/dashboard/summary`
4. Execute recovery: `POST /api/execution/execute` with `{"case_id": 1}`
5. Check audit logs: `GET /api/audit/`
