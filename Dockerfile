FROM python:3.13-slim

# Unbuffered output so container logs stream to Render in real time.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

# Dependencies are installed before the source is copied so that code changes
# don't invalidate the (slow) pip layer. Wheels are available for every pinned
# package on this base image, so no build toolchain is needed.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as an unprivileged user.
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

# Render injects $PORT and health-checks against it; the fallback keeps
# `docker run` working locally.
ENV PORT=8501
EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import os,urllib.request; \
        urllib.request.urlopen(f\"http://127.0.0.1:{os.environ['PORT']}/_stcore/health\")"

# Shell form so $PORT is expanded at runtime rather than baked in at build time.
CMD ["sh", "-c", "streamlit run app.py --server.port=$PORT --server.address=0.0.0.0"]
