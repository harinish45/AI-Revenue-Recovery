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
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.

If the backend environment is already installed:

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

Open `http://localhost:5173`.

The frontend connects to `http://localhost:8000` by default. To override it:

```text
VITE_API_BASE=http://localhost:8000
```

### 3. Production build check

```powershell
cd frontend
npm run build
```

### 4. Preview production build

```powershell
npm run preview
```

## 5-Minute Pitch Flow

1. Show **Razorpay Hackathon Sandbox | Test Mode Active | Simulated Gateway**.
2. Click **Seed Data** and show the recovery queue.
3. Point out live **At Risk**, **Recovered**, **Recovery Rate**, **Open Cases**, and **Escalated Cases**.
4. Click **Run Batch Recovery** and show the returned metrics modal and recovery toast.
5. Click **Arm Failure Simulation**. The control becomes red and explicitly says the next execution will escalate.
6. Execute an OPEN case.
7. Show the bright-red **ESCALATED TO HUMAN** badge and the human-review toast.
8. Click **View Compliance Audit** and show the backend events proving diagnosis, policy gating, execution, and escalation.

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

## Development Boundary

Backend and frontend are developed independently against the shared API contract. The backend is locked for the final demo; all pitch UI work belongs on `frontend-dev`. Do not add production payment credentials or real money movement to this project.
