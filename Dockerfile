FROM python:3.15.0b3-slim

WORKDIR /app

COPY requirements.txt requirements.txt

# Install build dependencies, compile Python packages, then remove build-only packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libffi8 \
    && pip install -r requirements.txt \
    && apt-get purge -y build-essential libffi-dev \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY src .

CMD ["python", "main.py"]
