# AGENTS & Autonomous Tool Conventions

## Project Rules & Architecture Invariants

1. **Architecture & Frameworks:**
   - Backend: FastAPI, Python 3.11+ (`backend/`).
   - Frontend: React 19, Tailwind CSS (`frontend/`).
   - Payment Gateway: Razorpay integration with test mode keys.

2. **Absolute Safety Invariants:**
   - LLMs must NEVER initiate money movement or financial debit transactions directly.
   - All actions require deterministic policy evaluation.
   - Every state transition must be logged to the immutable audit trail.
   - Run existing test suites (`pytest backend/tests`) to ensure 100% pass rate before committing.
