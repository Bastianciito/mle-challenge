# Builder
FROM python:3.14-slim-trixie AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml ./
RUN uv export --no-group dev --no-group test -o requirements.txt

# Euntime
FROM python:3.14-slim-trixie
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
COPY --from=builder /app/requirements.txt .
RUN uv run pip install -r requirements.txt
COPY challenge ./challenge
COPY artifacts ./artifacts
EXPOSE 8080
CMD ["python", "-m", "uvicorn", "challenge.api:app", "--host", "0.0.0.0", "--port", "8080"]