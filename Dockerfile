# Dockerfile pro ergonomic analysis Flask aplikaci
FROM python:3.9.18-slim

# System dependencies pro MediaPipe a OpenCV
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgtk-3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first pro better caching
COPY requirements.txt runtime.txt ./

# Instalace Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy zbytek aplikace
COPY . .

# Vytvoření storage directories
RUN mkdir -p /app/data/uploads /app/data/outputs /app/data/logs && \
    chmod 755 /app/data

# Environment proměnné  
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Exposne port
EXPOSE 8080

# Start aplikace
CMD ["python", "web_app.py"]