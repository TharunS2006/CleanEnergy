FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY static ./static
COPY data ./data

# The database lives on its own volume, separate from the bundled sample bill.
ENV DATABASE_URL=sqlite:////app/db/cloudpulse.db
RUN mkdir -p /app/db

EXPOSE 8000
CMD ["sh", "-c", "exec python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
