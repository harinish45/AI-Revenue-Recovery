<div align="center">

# 💰 RecoverAI

**Autonomous Revenue Recovery Agent**

[![CI](https://github.com/harinish45/AI-Revenue-Recovery/actions/workflows/ci.yml/badge.svg)](https://github.com/harinish45/AI-Revenue-Recovery/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](docker-compose.yml)

> *AI agent that detects failed payments and autonomously runs recovery workflows — without moving money*

`Detect → Diagnose → Decide → Recover → Audit`

[📋 TODO](TODO.md) · [📄 PRD](PRD.md) · [🚀 Deploy](DEPLOY.md)

</div>

---

## 🏗️ System Architecture

```mermaid
graph LR
    subgraph Triggers["⚡ Payment Events"]
        Stripe["💳 Stripe Webhook\n(payment_failed)"]
        Manual["👤 Manual Trigger"]
    end

    subgraph Backend["🐍 FastAPI Backend"]
        Ingest["📥 Event Ingestion"]
        Classifier["🤖 AI Failure Classifier\n(hard / soft / expired)"]
        Scorer["📊 Risk Scorer\n(churn probability)"]
        Orchestrator["🔀 Recovery Orchestrator"]
    end

    subgraph Recovery["🔄 Recovery Channels"]
        Email["📧 Email Sequence\n(SendGrid)"]
        SMS["📱 SMS\n(Twilio)"]
        InApp["🌐 In-App Prompt"]
        Retry["🔁 Smart Retry\n(ML-timed)"]
    end

    subgraph Analytics["📊 Analytics"]
        Dashboard["📈 Recovery Dashboard"]
        Audit["📋 Audit Log"]
    end

    Stripe --> Ingest
    Manual --> Ingest
    Ingest --> Classifier
    Classifier --> Scorer
    Scorer --> Orchestrator
    Orchestrator --> Email
    Orchestrator --> SMS
    Orchestrator --> InApp
    Orchestrator --> Retry
    Orchestrator --> Audit
    Audit --> Dashboard
```

---

## 🚀 Quick Start

```bash
git clone https://github.com/harinish45/AI-Revenue-Recovery.git
cd AI-Revenue-Recovery

# Linux/Mac
./bootstrap.sh

# Windows
./bootstrap.ps1

# Or Docker
docker compose up --build
```

---

## 📊 Recovery Flow State Machine

```mermaid
stateDiagram-v2
    [*] --> PaymentFailed
    PaymentFailed --> Classified: AI Diagnoses Failure
    Classified --> SoftDecline: Retry Possible
    Classified --> HardDecline: No Retry
    Classified --> ExpiredCard: Card Update Needed
    SoftDecline --> SmartRetry: Optimized Timing
    ExpiredCard --> CardUpdateRequest: Email + SMS
    SmartRetry --> Recovered: Payment Succeeds
    SmartRetry --> Churned: Max Retries Exceeded
    CardUpdateRequest --> Recovered: Card Updated
    HardDecline --> Churned: No Recovery Path
    Recovered --> [*]
    Churned --> [*]
```

---

## 📁 Structure

```
AI-Revenue-Recovery/
├── 🌐  frontend/          # React dashboard
├── 🐍  backend/           # FastAPI + ML models
├── 📊  docs/              # Architecture docs
├── 🔧  scripts/           # Automation scripts
├── 🐳  docker-compose.yml
└── 📋  RecoverAI-standalone.html  # Demo
```

---

<div align="center">
<a href="LICENSE">MIT License</a> · Built by harinish45
</div>