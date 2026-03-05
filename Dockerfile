FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY grid_guard.py .

# Run as non-root user
RUN useradd -m -u 1000 gridguard
USER gridguard

CMD ["python", "-u", "grid_guard.py"]
