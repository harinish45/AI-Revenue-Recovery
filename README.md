# RecoverAI

AI-powered revenue recovery for Razorpay Test Mode.

## Hackathon Track

**Track 03 — AI Revenue Recovery**

RecoverAI detects failed payments, determines a bounded recovery intervention, executes a safe recovery workflow, measures recovered revenue, and records an auditable trail.

## Repository Ownership

- `frontend/` — ChatGPT-owned frontend work
- `backend/` — Qwen-owned backend work
- `docs/` — shared architecture and API contract

## Safety Boundary

All financial actions are limited to Razorpay Test Mode / simulated gateway behavior. No production money movement is used for the hackathon demo. Secrets must never be committed.

## Architecture

```text
Failed Payment → Detect → Diagnose → Decide → Policy Gate → Recovery Action → Result → Audit → Metrics
```

## Run the Demo

### 1. Start the backend

From the repository root, use a terminal for the backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.

If the backend environment is already installed, the minimum startup command is:

```powershell
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Start the frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Vite will normally serve the dashboard at `http://localhost:5173`.

The frontend connects to `http://localhost:8000` by default. To override it, create `frontend/.env` with:

```text
VITE_API_BASE=http://localhost:8000
```

### 3. Verify the production build

```powershell
cd frontend
npm run build
```

### 4. Preview the production build locally

```powershell
cd frontend
npm run preview
```

## 5-Minute Pitch Flow

1. Open the dashboard and point out **Razorpay Hackathon Sandbox | Test Mode Active | Simulated Gateway**.
2. Click **Seed Data**.
3. Show the live risk, recovered amount, recovery rate, open cases and escalated cases.
4. Click **Run Batch Recovery** and show the backend-returned recovery metrics.
5. Click **Arm Failure Simulation**. The control turns red and warns that the next execution will escalate.
6. Execute an OPEN case.
7. Show the bright-red **ESCALATED TO HUMAN** state and the toast: **Escalated to Human Review due to gateway failure.**
8. Click **View Compliance Audit** and show the backend audit events proving the gated workflow.

## Verified API Contract

```text
POST /api/demo/seed
POST /api/demo/reset
GET  /api/dashboard/summary
GET  /api/cases/
POST /api/demo/recovery-batch
POST /api/demo/simulate-failure
POST /api/execution/execute
GET  /api/audit/
```

Execution payload:

```json
{"case_id":"<OPEN_CASE_ID>"}
```

The deterministic failure simulation returns `status: "needs_human_review"` and is rendered by the frontend as **ESCALATED TO HUMAN**.

## Development

Backend and frontend are developed independently against the shared API contract in `docs/api-contract.md`. The backend is locked for the final demo; frontend pitch polish lives on `frontend-dev`.
