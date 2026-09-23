# The course proxy as a container, for Carolina CloudApps (OpenShift) or any
# container host. Build from the repo root:
#     docker build -f proxy/Dockerfile -t dlc-proxy .
# Runs as a non-root user, listens on $PORT (8080), keeps its ledger under
# /data — mount a persistent volume there or the ledger dies with the pod.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/app/.venv \
    HOME=/tmp PORT=8080 DLC_PROXY_DB=/data/dlc_proxy.db

RUN pip install --no-cache-dir "uv>=0.8"

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY dlc ./dlc
COPY proxy ./proxy

# OpenShift starts containers as an arbitrary UID in group 0: everything the
# proxy touches must be group-writable, and nothing may assume a username.
RUN mkdir -p /data && chgrp -R 0 /app /data && chmod -R g=u /app /data
USER 1001

EXPOSE 8080
HEALTHCHECK --interval=60s --timeout=5s CMD ["/app/.venv/bin/python", "-c", \
    "import urllib.request,os; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8080\")}/v1/health', timeout=4)"]
CMD ["sh", "-c", "exec /app/.venv/bin/uvicorn proxy.dlc_proxy:app --host 0.0.0.0 --port ${PORT:-8080}"]
