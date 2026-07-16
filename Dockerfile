FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as an unprivileged user; executed user code should never have container root.
RUN useradd --create-home --uid 10001 docsport \
    && mkdir -p /app/data /app/logs \
    && chown -R docsport:docsport /app
USER docsport

EXPOSE 8500

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:8500/api/health', timeout=2); sys.exit(0)" || exit 1

CMD ["python", "main.py", "--port", "8500"]
