
# 🎬 myanimesite

myanimesite is a Django-based modular-monolith application for browsing, organizing, and interacting with anime content. It aggregates content data from external API.

The system provides advanced filtering, personalized user features, and integrates with external APIs for content aggregation.

> Note: The project is under active development.



## 📦 Tech Stack
**Server:** Python, Django, PostgreSQL, Redis, Celery

**Integrations:** Stripe, Elasticsearch, OAuth2 

**Client:** JavaScript, TailwindCSS, DjangoTemplates



## ✨ Features

**Core:**
- Customizable user profiles
- Private and public scope for user profiles
- Comments under the titles
- System of user followings / followers
- Personal customizable folders for managing titles 
- Watching history for authorized users

**Advanced:**
- Social authentication
- External API integration for automated content ingestion
- Filtering and sorting of movie content
- Smart search functionality of titles and users
- Subscription and payment system
- Auto updating charts and recommendations of titles



## 🧠 Tech Highlights
- Designed relational database models for scalable content management
- Built complex and optimized query chains using Django ORM
- Implemented caching and performance optimizations for heavy views
- Integrated Celery and Redis for asynchronous background task processing
- Developed user activity tracking system (watch history and progress tracking)
- Built nested comment system with hierarchical structure and interactions
- Structured backend logic into reusable modules, services, and querysets
- Built server-side filtering and sorting logic for large datasets
- Integrated Stripe for subscription-based payments and implemented webhook handling



## 📈 Overall Growth
Each part of this project helped me understand more about building apps, managing complex information, and implementing high-functionality. I looked at this project through the lens of production, working out the little things that users pay attention to. It was more than just making a web-site. It was about solving problems, learning new things, and improving my skills for future work.



## 💭 How can it be improved?

- Add REST API layer (Django REST Framework)
- Add much flexible Kinopoisk API manipulation
- Improve admin panel
- Add censorship validation of comments
- Extend analytics (user behavior, preferences)



## 🚦Running the Project
1. Clone the repository to your local machine.
2. Create virtual environment.
3. Run ```pip install -r requirements.txt``` to install required dependencies.
4. Run ```cp .env.example .env``` to set up your env variables.
5. Run ```python manage.py migrate``` to apply project migrations
6. Create superuser by running ```python manage.py createsuperuser``` and follow appeared steps
7. Finally, run ```python manage.py runserver``` and open [http:/localhost:8000](http:/localhost:8000).



## 🗃️ Integrations
The project requires installation of the following integrations.

### Redis
Start Redis server before running the project.
Run ```redis-cli```.

### Celery
If Redis was connected successfully, run ```celery -A <your_project> worker --pool=solo --loglevel=info``` or ```celery -A <your_project> worker -l info```.

### Elasticsearch
```bash
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -p 9300:9300 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  elasticsearch/elasticsearch:9.0.3
```
### Stripe 
Run ```stripe listen --forward-to localhost:8000/webhook/stripe/```.
Use the provided webhook secret in your .env.

## 🧪 Testing

```python manage.py test .```

