FROM python:3.14-slim-trixie
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY challenge ./challenge
RUN uv sync --frozen --no-dev
EXPOSE 8080
CMD ["uv", "run", "uvicorn", "challenge.api:app", "--host", "0.0.0.0", "--port", "8080"]