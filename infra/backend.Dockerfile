FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt backend/constraints.txt /app/
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home --uid 10001 appuser
COPY backend /app
RUN mkdir -p /app/data/media && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log"]
