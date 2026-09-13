# Microsoft's official Playwright image ships Chromium and its exact
# matching system dependencies pre-installed and tested together for this
# playwright version -- avoids package-name mismatches (renamed font
# packages, etc.) that `playwright install --with-deps` can hit when run
# against an arbitrary base image's package repos.
FROM mcr.microsoft.com/playwright/python:v1.49.1-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
