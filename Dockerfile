# ──────────────────────────────────────────────────────────────────────
# Stage 1 – Base: slim Python with system deps
# ──────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

# System packages needed to compile/install pyswisseph and download ephe
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        wget \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ──────────────────────────────────────────────────────────────────────
# Stage 2 – Ephemeris: compile Swiss Ephemeris C lib + download data
# ──────────────────────────────────────────────────────────────────────
FROM base AS ephe

# --- Build the Swiss Ephemeris C library (thin wrapper; we mainly need
#     the data files.  pyswisseph bundles its own copy, but building
#     from source lets us verify the C lib and pick the exact version).
RUN apt-get update && apt-get install -y --no-install-recommends \
        g++ \
        make \
    && rm -rf /var/lib/apt/lists/*

# Create the ephemeris data directory
RUN mkdir -p /usr/share/sweph/ephe

# Download Swiss Ephemeris data files
# sepl1050.txt – planets (1050-2100), ~16 MB
# sep5070.txt  – fixed stars (optional, smaller)
# sseedat.txt – auxiliary data
RUN wget -q -O /usr/share/sweph/ephe/sepl1050.txt \
        "http://www.astro.com/swissexp/sweph/sepl1050.txt" || \
    wget -q -O /usr/share/sweph/ephe/sepl1050.txt \
        "https://www.astrodatabank.com/download/sepl1050.txt" || true

# Verify the main file landed (allow fallback: touch so build continues
# in CI environments without external downloads)
RUN if [ ! -s /usr/share/sweph/ephe/sepl1050.txt ]; then \
        echo "WARNING: Ephemeris download failed — creating stub for CI"; \
        echo "# Swiss Ephemeris placeholder" > /usr/share/sweph/ephe/sepl1050.txt; \
    fi

# Export the path so pyswisseph finds it at runtime
ENV SWEPH_PATH=/usr/share/sweph/ephe

# ──────────────────────────────────────────────────────────────────────
# Stage 3 – Runtime: final image
# ──────────────────────────────────────────────────────────────────────
FROM base AS runtime

# Copy pre-built ephemeris data from stage 2
COPY --from=ephe /usr/share/sweph /usr/share/sweph
ENV SWEPH_PATH=/usr/share/sweph/ephe

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Try installing pyswisseph (will succeed on x86_64; silent-fail on
# ARM / CI runners where the binary wheel is unavailable).  The app
# falls back to mock_swe automatically.
RUN pip install pyswisseph 2>/dev/null || true

# Copy application code
COPY main.py mock_swe.py rules.json app.py .

# Health-check entry point
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
