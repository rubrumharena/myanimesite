- There is a problem in caching of the full page in titles.views.IndexView.
- In services.kinopoisk_import.py, there is a problem with assemble_atomic: in some cases rating can be empty
```python
statistic = Statistic(
            kp_rating=obj.ratings['kp'],
            kp_votes=obj.votes['kp'],
            imdb_rating=obj.ratings['imdb'],
            imdb_votes=obj.votes['imdb'],
            title=title,
        )
```
- Update Kinopoisk API. Data fields could be too old at present 