FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy all source and install
COPY . .
RUN pip install --no-cache-dir .

CMD ["python", "-m", "app.main"]
