# ==============================================================================
# Quantum-Safe Hybrid VPN Testbed - Docker Containerfile
# Base Image: Python 3.13 Slim (Debian-based, minimal attack surface)
# ==============================================================================
FROM python:3.13-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install security updates and cryptographic dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install required Python cryptographic libraries
RUN pip install --no-cache-dir cryptography

# Create non-root user for DevSecOps least-privilege container execution
RUN useradd -m -u 1001 vpnuser

# Copy application source code
COPY . /app

# Ensure proper permissions
RUN chown -R vpnuser:vpnuser /app

# Run cryptographic test suite during container build to verify correctness
RUN python test_pipeline.py

# Switch to non-root user
USER vpnuser

# Expose VPN Exit Gateway Port (Default: 8888)
EXPOSE 8888

# Healthcheck to verify gateway responsiveness
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8888/ || exit 1

# Launch Cloud Gateway Server
ENTRYPOINT ["python", "cloud_server.py"]
CMD ["--port", "8888"]
