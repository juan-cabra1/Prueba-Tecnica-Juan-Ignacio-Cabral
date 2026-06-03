FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir .

COPY app/ ./app/
COPY docs/ ./docs/

CMD ["uvicorn", "app.interface.api:app", "--host", "0.0.0.0", "--port", "8000"]
