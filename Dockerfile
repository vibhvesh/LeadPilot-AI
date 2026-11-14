# syntax=docker/dockerfile:1

FROM python:3.12.16-slim AS build

ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1

RUN python -m venv /opt/venv

RUN --mount=type=bind,source=requirements.txt,target=/tmp/requirements.txt \
    --mount=type=cache,target=/root/.cache/pip \
    pip install --no-compile -r /tmp/requirements.txt

FROM python:3.12.16-slim AS runtime

ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp

WORKDIR /app

RUN groupadd --system --gid 1001 appuser \
    && useradd --system --uid 1001 --gid appuser --no-create-home --shell /usr/sbin/nologin appuser

COPY --from=build --link --chown=1001:1001 /opt/venv /opt/venv
COPY --link --chown=1001:1001 app /app/app

USER appuser

EXPOSE 1102

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:1102/health', timeout=4)"]

LABEL org.opencontainers.image.title="LeadPilot AI" \
      org.opencontainers.image.source="https://github.com/vibhvesh/LeadPilot-AI" \
      org.opencontainers.image.description="CanberraAI LeadPilot"

ENTRYPOINT ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "1102", "--proxy-headers", "--forwarded-allow-ips", "*"]
