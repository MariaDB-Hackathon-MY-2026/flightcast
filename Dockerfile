# syntax=docker/dockerfile:1.7
# ============================================================
# Stage 1 — builder
# Installs all Python dependencies into an isolated prefix so
# only the compiled packages are copied to the runtime stage.
# ============================================================
FROM python:3.11-slim AS builder

# Install OS build deps needed by the mariadb connector C
# extension and other compiled wheels (xgboost, lightgbm).
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        libmariadb-dev \
        libmariadb-dev-compat \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy only the requirements file first — this layer is cached
# until requirements.txt changes, making rebuilds fast.
COPY requirements.txt .

# Install into /install so the runtime stage can COPY it wholesale.
RUN pip install --upgrade pip setuptools wheel \
    && pip install --prefix=/install --no-cache-dir -r requirements.txt

# ============================================================
# Stage 2 — runtime
# Minimal image: no build tools, no compiler, no root process.
# ============================================================
FROM python:3.11-slim AS runtime

LABEL org.opencontainers.image.title="FlightCast" \
      org.opencontainers.image.description="Conformal prediction for aviation demand — MariaDB Hackathon Malaysia 2026" \
      org.opencontainers.image.authors="TP070056@mail.apu.edu.my"

# Runtime OS libs required by the mariadb connector binary.
# curl is needed for Docker healthcheck probes.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libmariadb3 \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy compiled site-packages from the builder stage.
COPY --from=builder /install /usr/local

# Create a dedicated non-root user and group.
RUN groupadd --gid 10001 appgroup \
    && useradd --uid 10001 --gid appgroup \
               --shell /sbin/nologin \
               --no-create-home appuser

WORKDIR /app

# Make the flightcast package importable from /app/src/flightcast
ENV PYTHONPATH=/app/src

# Copy application source. The docker-compose.yml bind-mounts
# ./src at runtime so this COPY covers the bootstrap/seed script
# and any files that must exist before the mount kicks in.
COPY --chown=appuser:appgroup src/ ./src/

# Expose both Streamlit and FastAPI ports so the image is
# self-documenting; the actual binding is set via CMD/command.
EXPOSE 8501 8000

USER appuser

# Default entrypoint — docker-compose overrides this via `command`.
# Keeping it explicit so `docker run` works standalone too.
CMD ["streamlit", "run", "src/flightcast/ui/app.py", \
     "--server.port=8501", "--server.address=0.0.0.0"]
