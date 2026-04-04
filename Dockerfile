FROM python:3.12-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt


FROM base AS runtime

COPY --chmod=755 entrypoint.sh /app/entrypoint.sh
COPY alembic.ini /app/alembic.ini
COPY migrations /app/migrations
COPY app /app/app

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "-m", "app"]


FROM base AS test

COPY requirements-dev.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements-dev.txt

COPY --chmod=755 entrypoint.sh /app/entrypoint.sh
COPY alembic.ini /app/alembic.ini
COPY migrations /app/migrations
COPY app /app/app
COPY tests /app/tests
COPY pytest.ini /app/pytest.ini
COPY .env.test /app/.env.test

CMD ["pytest", "-q"]