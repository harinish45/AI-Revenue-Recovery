FROM python:3.14-slim

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# main.py resolves RecoverAI-standalone.html two directories above backend/app,
# so the build context must be the repo root, not backend/ — see docker-compose.yml.
COPY backend/ backend/
COPY RecoverAI-standalone.html RecoverAI-standalone.html

# Run as an unprivileged user; the app never needs root inside the container.
RUN useradd --no-create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

WORKDIR /app/backend
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/api/health', timeout=3)" || exit 1

# --proxy-headers/--forwarded-allow-ips trust the platform's reverse proxy (TLS
# terminates there) so slowapi's get_remote_address sees the real client IP
# instead of the proxy's, which would otherwise bucket every client together.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
