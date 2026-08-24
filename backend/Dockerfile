FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# main.py resolves RecoverAI-standalone.html two directories above backend/app,
# so the build context must be the repo root, not backend/ — see docker-compose.yml.
COPY backend/ backend/
COPY RecoverAI-standalone.html RecoverAI-standalone.html

WORKDIR /app/backend
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
