FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TZ=Pacific/Auckland DATA_DIR=/data HOME=/tmp XDG_CACHE_HOME=/tmp
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY dns_host.py .
COPY CHANGELOG.md .
COPY templates ./templates
COPY static ./static
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "4", "--timeout", "60", "--access-logfile", "-", "app:app"]
COPY tests ./tests
COPY .env.example README.md ./
COPY scripts ./scripts
COPY docs ./docs
COPY README.md .
COPY compose.yaml .

USER 0
COPY Dockerfile .
RUN chmod -R a+rX /app
USER 10001:10001
