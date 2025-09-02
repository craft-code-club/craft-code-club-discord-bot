FROM python:3.14.0rc2-slim

WORKDIR /app

COPY requirements.txt requirements.txt

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install -r requirements.txt

COPY src .

CMD ["python", "main.py"]
