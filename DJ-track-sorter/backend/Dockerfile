# ffmpeg is required for librosa/audioread to decode MP3s. Render/Railway's
# native Python buildpacks don't include it, so we deploy via this Dockerfile
# (both platforms support Docker on their free tiers, no paid plan needed).
FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
