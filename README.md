# RecoverAI — AI Revenue Recovery Platform

[![Razorpay Hackathon](https://img.shields.io/badge/Razorpay_Hackathon-Track_03-3d5af1.svg)](https://razorpay.com)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com)
[![React 18](https://img.shields.io/badge/React-18-61dafb.svg)](https://react.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **RecoverAI** is an intelligent revenue recovery control center designed for **Razorpay Track 03 — AI Revenue Recovery**.
> It transforms unstructured payment failure signals into diagnosed root causes, executes policy-guarded recovery interventions, and produces an immutable compliance audit trail.

---

## 🌟 Pitch & Core Design Philosophy

> **"We use AI strictly where unstructured text or error parsing is needed to diagnose root causes. For actual recovery execution, we intentionally built a deterministic, rules-based state machine."**

1. **AI Intake & Diagnosis Layer**: Multi-provider LLM chain parses raw gateway failure codes and customer metrics into structured diagnosis, confidence, and recommended interventions.
2. **Deterministic Policy Safety Layer**: Financial guardrails prevent unsafe retries (e.g. invalid cards, high-risk amounts, PCI compliance limits). The AI recommends; the policy engine decides.
3. **Bounded Recovery Executor**: Executes retry links, split payments, card updates, or escalations via Razorpay adapter.
4. **Immutable Audit Trail**: Every AI decision, policy check, and gateway interaction is logged for judge inspection and financial compliance.

---

## ⚡ Multi-Provider AI Fallback Chain

RecoverAI features zero-downtime AI diagnosis via a failover chain:

```
[Payment Failure]
       ↓
 1. Groq (llama-3.1-70b-versatile)
       ↓ (if 429 rate limit / timeout / no key)
 2. OpenRouter (llama-3.1-70b-instruct)
       ↓ (if unavailable)
 3. Nvidia NIM (llama-3.1-70b-instruct)
       ↓ (if unavailable)
 4. OpenAI (gpt-4o-mini)
       ↓ (if all unavailable)
 5. Deterministic Fallback Engine (Zero API Keys Needed)
```

- **Works 100% locally with ZERO API keys** (falls back gracefully to deterministic diagnosis engine).
- **Supports API keys** for Groq, OpenRouter, Nvidia NIM, or OpenAI in `backend/.env`.

---

## 🚀 One-Command Quickstart

### Prerequisites
- Node.js 18+
- Python 3.10+

### Run Demo (One Command)
```bash
npm run demo
```
This script automatically:
1. Verifies Python & Node environments.
2. Installs backend (`requirements.txt`) and frontend (`package.json`) dependencies.
3. Starts the FastAPI backend on port `8000`.
4. Starts the Vite React dashboard on port `5173`.
5. Performs a health check on both services.

Access the platform at:
- **Dashboard**: [http://localhost:5173](http://localhost:5173)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 🎛️ Demo Controls (Dashboard)

- **Seed Demo Data**: Generates 100 deterministic payment failures with complete customer metadata.
- **Run Batch Recovery**: Executes policy-guarded AI recovery across all open cases in one click.
- **Arm Failure Simulation**: Simulates gateway infrastructure failure to demonstrate automatic escalation to human review (`NEEDS_HUMAN_REVIEW`).
- **View Compliance Audit**: Inspect real-time audit logs detailing LLM provider used, policy check outcomes, and execution details.
- **Reset Demo**: Clears all database tables and resets simulation state.

---

## 🧪 Testing

Run backend pytest suite (44 unit & integration tests):
```bash
cd backend
python -m pytest tests/ -v
```

---

## 📁 Repository Structure

```
.
├── backend/
│   ├── app/
│   │   ├── core/           # Core configuration & settings
│   │   ├── models.py       # SQLAlchemy ORM schemas
│   │   ├── schemas.py      # Pydantic v2 validation models
│   │   ├── database.py     # SQLite connection & session
│   │   ├── main.py         # FastAPI app & routing
│   │   ├── routers/        # API endpoints (cases, dashboard, execution, audit, demo)
│   │   └── services/       # AI provider chain, policy engine, recovery executor
│   ├── tests/              # Pytest test suite (44 tests)
│   └── requirements.txt
├── frontend/
│   ├── src/                # React dashboard (Inter font, dark fintech theme)
│   │   ├── components/     # MetricsGrid, ActionCenter, CasesTable, AuditDrawer, etc.
│   │   └── services/api.js # Normalized API client
│   └── package.json
├── scripts/
│   └── start-demo.js       # One-command demo launcher
├── railway.toml            # Railway.app PaaS deployment config
├── render.yaml             # Render.com PaaS deployment config
└── package.json            # Root npm orchestration
```

---

## 🛡️ License

MIT License. Developed for Razorpay Hackathon Track 03.
