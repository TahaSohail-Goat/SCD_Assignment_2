FROM python:3.12.16-slim-bookworm
ARG VCS_REF=development
LABEL org.opencontainers.image.revision=${VCS_REF}
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends tesseract-ocr poppler-utils && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd -u 10001 -m rahbar
COPY pipeline ./pipeline
USER 10001:10001
CMD ["python", "-m", "pipeline.run"]
