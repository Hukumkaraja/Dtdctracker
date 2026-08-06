# Playwright's official image already has Chromium + every system
# library it needs pre-installed, so we don't need `--with-deps` or
# apt/sudo access — this is what makes Render's build succeed reliably.
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY dtdc_bot.py .

# Render sets $PORT at runtime; the bot's health-check server reads it.
CMD ["python", "dtdc_bot.py"]
