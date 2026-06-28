#!/bin/bash
set -e

# Generate .streamlit/secrets.toml from environment variables at container start.
# Render (and Railway) inject secrets as env vars; Streamlit's st.secrets reads
# this file, so we bridge the two here.
mkdir -p .streamlit

cat > .streamlit/secrets.toml <<TOML
PAGESPEED_API_KEY = "${PAGESPEED_API_KEY}"
SERPER_API_KEY    = "${SERPER_API_KEY}"
GEMINI_API_KEY    = "${GEMINI_API_KEY}"
ADMIN_PASSWORD    = "${ADMIN_PASSWORD}"
UPSTASH_REDIS_REST_URL   = "${UPSTASH_REDIS_REST_URL}"
UPSTASH_REDIS_REST_TOKEN = "${UPSTASH_REDIS_REST_TOKEN}"
SCRAPER_API_KEY  = "${SCRAPER_API_KEY:-}"
ZENROWS_API_KEY  = "${ZENROWS_API_KEY:-}"
TOML

exec streamlit run app.py \
    --server.port="${PORT:-8501}" \
    --server.address=0.0.0.0 \
    --server.headless=true
