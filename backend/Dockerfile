FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# NOTE: run as a non-root user in the PRODUCTION image only. The dev compose
# bind-mounts host ./backend into /app, so a non-root process can't write the
# host-owned files it regenerates (structure cache). See SECURITY.md #12.

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000"]
