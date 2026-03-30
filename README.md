
# 🎬 myanimesite

myanimesite is a Django-based modular-monolith. The web-application makes sence for anime viewers who interested in tools for browsing, organizing, and interacting with titles through advanced filtering and search. It aggregates content data from external API.

> Note: The project is under active development.


## 📦 Tech Stack
**Server:** Python, Django, PostgeSQL, Redis, Celery

**Integrations:** Stripe, Elsticsearch, OAuth2 

**Client:** JavaScript, TailwindCSS, DjangoTemplates




## ✨ Features

- Advanced filtering and sorting of movie content
- Smart search functionality of titles and users
- Social authentication
- Subscription and payment system
- Private and public user profiles
- Auto updating charts and recommendations of titles
- Custom admin interface for insertion titles from external API
- Comments under the titles
- System of user followings / followers
- Personal customizable folders for managing titles 
- Watching history for authorized users
- Customizable user profiles



## 🚦Running the Project
1. Clone the repository to your local machine.
2. Create virtual environment.
3. Run ```pip install -r requirements.txt``` to install required dependencies.
4. Run ```cp .env.example .env``` to set up your env veriables.
5. Run ```python manage.py migrate``` to apply project migrations
6. Create superuser by running ```python manage.py createsuperuser``` and follow apeared steps
7. Finally, run ```python manage.py runserver``` and open [http:/localhost:8000](http:/localhost:8000).



## 🗃️ Integrations
The project requires instalation of the following integrations.

### 🟥 Redis
Run ```redis-cli```.

### 💚 Celery
If Redis was connected seccessfully, you is able to turn on backround tasks by running ```celery -A <your_project> worker --pool=solo --loglevel=info``` or ```celery -A <your_project> worker -l info```.

### 🔍 Elasticsearch
As it was mentioned above, the project uses Elasticsearch for search functionality, and some other functionalities depend on it due to indexing. So, run this docker container:

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
Use the provided webhook secret in your .env.

## 🧪 Testing

Run ```python manage.py test .``` to test the configured project (it can take up 5 min )

