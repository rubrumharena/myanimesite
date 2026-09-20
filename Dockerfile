FROM node:22-slim AS frontend

WORKDIR /build

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

RUN npx @tailwindcss/cli -i tailwind/input.css -o static/vendor/css/output.css --minify


FROM python:3.11.9-slim

WORKDIR /app

RUN useradd -m app

COPY requirements.txt .

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*
RUN pip install -r requirements.txt

COPY . .
COPY --from=frontend /build/static/vendor/css/output.css /app/static/vendor/css/output.css

RUN SECRET_KEY=build POSTGRES_DB=x POSTGRES_USER=x POSTGRES_PASSWORD=x \
    python manage.py collectstatic --noinput
RUN mkdir -p /app/staticfiles /app/media && chown -R app:app /app/staticfiles /app/media

USER app
CMD ["gunicorn", "myanimesite.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]