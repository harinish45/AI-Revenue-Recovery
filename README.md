# RecoverAI

AI-powered revenue recovery for Razorpay Test Mode.

## Hackathon Track

**Track 03 — AI Revenue Recovery**

RecoverAI detects failed payments, determines a bounded recovery intervention, executes a safe recovery workflow, measures recovered revenue, and records an auditable trail.

## Repository Ownership

- `frontend/` — ChatGPT-owned frontend work
- `backend/` — Qwen-owned backend work
- `docs/` — shared architecture and API contract

## Primary Workflow

Failed Payment → Detect → Diagnose → Decide → Policy Gate → Recovery Action → Result → Audit → Metrics

## Safety Boundary

All financial actions are limited to Razorpay Test Mode/demo behavior. Secrets must be supplied through environment variables and must never be committed.

## Development

Backend and frontend are developed independently against the shared API contract in `docs/api-contract.md`.
