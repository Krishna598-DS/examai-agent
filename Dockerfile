# Every Dockerfile starts with FROM — the base image we build on top of.
# We use the official Python 3.12 slim image.
# "slim" means it has Python but strips out unnecessary tools,
# making the image smaller (~150MB vs ~900MB for the full image).
# Smaller images = faster deploys, less attack surface, lower storage costs.
FROM python:3.12-slim

# Set environment variables that affect Python behavior inside the container.
# PYTHONDONTWRITEBYTECODE=1 — don't create .pyc compiled files
#   Why? Containers are ephemeral — compiled files don't persist anyway
# PYTHONUNBUFFERED=1 — don't buffer stdout/stderr
#   Why? Without this, logs appear in batches rather than in real time.
#   In production you want logs immediately when they happen.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# WORKDIR sets the working directory inside the container.
# All subsequent commands run from this directory.
# /app is the convention — clear and simple.
WORKDIR /app

# Install system dependencies that some Python packages need to compile.
# We do this BEFORE copying our code because this layer changes rarely.
# Docker caches layers — if requirements.txt changes, Docker only
# reruns from that COPY line forward, not the apt install.
# This ordering (system deps → python deps → code) is the standard
# optimization pattern for fast rebuilds.
RUN apt-get update && apt-get install -y \
    # gcc is needed to compile some Python packages with C extensions
    gcc \
    # curl is useful for health checks inside the container
    curl \
    # clean up apt cache to reduce image size
    && rm -rf /var/lib/apt/lists/*

# Copy ONLY requirements first — before copying the rest of the code.
# Why? If your code changes but requirements don't, Docker uses the
# cached pip install layer. This makes rebuilds much faster.
COPY requirements.txt .

# Install Python dependencies.
# --no-cache-dir: don't save pip's download cache in the image
#   (reduces image size — we don't need the cache after installing)
# --upgrade pip: ensure we have the latest pip before installing
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Now copy the rest of the application code.
# This layer changes most often, so it goes last.
# The dot on the left = "everything in current directory"
# The dot on the right = "into WORKDIR (/app)"
COPY . .

# Create the data directory for ChromaDB
# We do this inside the image so the directory exists when container starts
RUN mkdir -p data/chroma

# Tell Docker this container listens on port 8000.
# EXPOSE is documentation — it doesn't actually open the port.
# The actual port mapping happens when you run the container.
EXPOSE 8000

# HEALTHCHECK tells Docker how to verify the container is working.
# Every 30 seconds, Docker runs this command inside the container.
# If it fails 3 times in a row, Docker marks the container as "unhealthy".
# This is how orchestrators like Kubernetes know to restart a broken container.
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# CMD is the command that runs when the container starts.
# We use the list form (not string form) — it avoids shell interpretation issues.
# --workers 1: one worker process (we'll scale with multiple containers, not workers)
# --host 0.0.0.0: accept connections from outside the container
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
