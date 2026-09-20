# 🎬 myanimesite

myanimesite is a Django-based modular monolith for anime viewers who want tools for browsing, organizing, and interacting with titles through advanced filtering and search. Content data is aggregated from external APIs.

> Note: The project is under active development.

## 📦 Tech Stack

**Server:** Python 3.11, Django 5.2, PostgreSQL, Redis, Celery, Gunicorn, WhiteNoise

**Integrations:** Stripe, Elasticsearch, OAuth2 (Google, GitHub), Kinopoisk API, TMDB

**Client:** JavaScript, TailwindCSS, Flowbite, Django Templates

**Infrastructure:** Docker, Docker Compose, Nginx, GitHub Actions

## ✨ Features

- Advanced filtering and sorting of movie content
- Smart search of titles and users
- Social authentication
- Subscription and payment system
- Private and public user profiles
- Auto-updating charts and recommendations of titles
- Custom admin interface for importing titles from external APIs
- Comments under the titles
- System of user followings / followers
- Personal customizable folders for managing titles
- Watching history for authorized users
- Customizable user profiles
- Multilanguage interface (English / Russian)

## 🗂️ Project Structure

| App             | Responsibility                                            |
|-----------------|-----------------------------------------------------------|
| `titles`        | Titles catalog, filtering, search documents               |
| `users`         | User profiles, followings / followers                     |
| `accounts`      | Authentication, email verification, password recovery     |
| `lists`         | Personal folders and collections of titles                |
| `comments`      | Comment trees under the titles                            |
| `video_player`  | Video playback                                            |
| `subscriptions` | Stripe subscriptions and webhooks                         |
| `services`      | Kinopoisk / TMDB clients and titles import tasks          |
| `common`        | Shared models, views, utils and validators                |

## 🚦 Running the Project

### 🐳 With Docker (recommended)

1. Clone the repository to your local machine.
2. Run ```cp .env.example .env``` and fill in your environment variables (see [Environment](#-environment)).
3. Run ```docker compose -f services.local.yaml up --build```.
4. Create a superuser: ```docker compose -f services.local.yaml exec web python manage.py createsuperuser```.
5. Open [http://localhost:8000](http://localhost:8000).

This starts the web server, PostgreSQL, Redis, Elasticsearch, a Celery worker and Celery beat. Migrations are applied and the search index is rebuilt automatically on startup.

### 🖥️ Manually

1. Clone the repository to your local machine.
2. Create and activate a virtual environment.
3. Run ```pip install -r requirements.txt``` to install the required dependencies.
4. Run ```npm install``` and then ```npm run dev``` to build and watch TailwindCSS styles.
5. Run ```cp .env.example .env``` and fill in your environment variables.
6. Start the [integrations](#-integrations) below.
7. Run ```python manage.py migrate``` to apply migrations.
8. Run ```python manage.py search_index --rebuild``` to build the Elasticsearch indexes.
9. Create a superuser by running ```python manage.py createsuperuser``` and follow the steps.
10. Finally, run ```python manage.py runserver``` and open [http://localhost:8000](http://localhost:8000).

## 🔐 Environment

Copy `.env.example` to `.env`. The main groups of variables:

| Group         | Variables                                                                                     |
|---------------|-----------------------------------------------------------------------------------------------|
| Django        | `DEBUG`, `SECRET_KEY`, `DOMAIN_NAME`                                                          |
| Database      | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DATABASE_HOST`, `DATABASE_PORT`         |
| External APIs | `KINOPOISK_TOKEN`, `TMDB_API_KEY`                                                             |
| Elasticsearch | `ELASTICSEARCH_HOST`, `ELASTICSEARCH_PORT`, `ELASTICSEARCH_USER`, `ELASTICSEARCH_SECRET`      |
| Redis         | `REDIS_HOST`, `REDIS_PORT`                                                                    |
| Email         | `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`         |
| Stripe        | `STRIPE_PUBLIC_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`                             |

For Google OAuth, add your client secret JSON file from Google Cloud to the project root separately.

## 🗃️ Integrations

The project requires the following integrations. With Docker they are started for you, except Stripe.

### 🟥 Redis
Run ```redis-cli``` to make sure the server is up. Redis is used as a cache and as the Celery broker.

### 💚 Celery
If Redis was connected successfully, you can turn on background tasks by running ```celery -A myanimesite worker --pool=solo --loglevel=info``` (Windows) or ```celery -A myanimesite worker -l info```.

Periodic tasks (updating titles from external APIs) are scheduled by beat: ```celery -A myanimesite beat --loglevel=info```.

### 🔍 Elasticsearch
The project uses Elasticsearch for search functionality, and some other features depend on it due to indexing. Run this docker container:

```bash
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -p 9300:9300 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  elasticsearch/elasticsearch:9.0.3
```

### 💳 Stripe
Run ```stripe listen --forward-to localhost:8000/webhook/stripe/```.
Use the provided webhook secret in your `.env`.

## 🧪 Testing

Run ```python manage.py test``` to test the configured project (it can take up to 5 min).

Code style is checked with [Ruff](https://docs.astral.sh/ruff/): ```ruff check .```

## 🚀 Deployment

Every push to `main` runs the CI pipeline (`.github/workflows/ci.yaml`): **lint → test → build**. On success the Docker image is built (TailwindCSS is compiled inside it) and pushed to Docker Hub.

The production stack is described in `services.prod.yaml`:

- `web` - Gunicorn serving the Django app, static files are served by WhiteNoise
- `nginx` - reverse proxy that also serves user-uploaded media files
- `worker` / `beat` - Celery worker and scheduler
- `postgres`, `redis`, `elastic` - data services with persistent volumes

```bash
docker compose -f services.prod.yaml up -d
```
