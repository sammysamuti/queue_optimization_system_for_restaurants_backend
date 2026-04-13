FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# We run as root so we can write migrations into /app (bind-mounted from host)
# No non-root user here.

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy project code
COPY . .

# Expose port
EXPOSE 4400

# Wait for DB, then run migrations & start gunicorn
CMD ["sh", "-c", "\
  echo 'Waiting for db...' && \
  while ! nc -z db 5432; do sleep 1; done && \
  python manage.py makemigrations && \
  python manage.py migrate --noinput && \
  python manage.py collectstatic --noinput && \
  gunicorn config.wsgi:application --bind 0.0.0.0:4400 --workers 3 \
"]
