FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libportaudio2 && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt backend/constraints.txt /app/
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home --uid 10001 appuser
COPY backend /app
RUN mkdir -p /app/data/media && chown -R appuser:appuser /app
USER appuser
ENV POSE_MODEL_PATH=/app/models/pose_landmarker_lite.task
RUN python -m app.vision.provider
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
