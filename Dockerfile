# ── Stage: final image ──────────────────────────────────────────────────────
FROM python:3.11-slim

# Avoid interactive prompts from apt / tzdata
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ── System packages ──────────────────────────────────────────────────────────
# curl + ca-certs are needed by pip / playwright downloader.
# The rest are the Chromium system libraries listed in packages.txt plus a few
# more that `playwright install-deps chromium` would normally install via apt.
# We pre-install them here so the Playwright step is a pure download, not an
# apt-get, which makes layer caching cleaner and avoids any "apt not available"
# edge cases on some container runtimes.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    # Chromium / Playwright system deps (superset of packages.txt)
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxext6 \
    fonts-liberation \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libglib2.0-0 \
    libpixman-1-0 \
    libpng16-16 \
    libxrender1 \
    libfreetype6 \
    xdg-utils \
 && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ──────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt playwright

# ── Playwright / Scrapling browser install ───────────────────────────────────
# `scrapling install` = playwright install chromium && playwright install-deps chromium
# We set PLAYWRIGHT_BROWSERS_PATH so the browser lands in a predictable layer.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN python -m playwright install chromium \
 && python -m playwright install-deps chromium

# ── Application code ─────────────────────────────────────────────────────────
COPY . .

# ── Entrypoint ───────────────────────────────────────────────────────────────
RUN chmod +x entrypoint.sh
EXPOSE 8501
ENTRYPOINT ["./entrypoint.sh"]
