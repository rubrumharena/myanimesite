from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

from .models import User


@registry.register_document
class UserDocument(Document):
    name = fields.TextField(analyzer='russian')

    class Index:
        name = 'user'
        settings = {'number_of_shards': 1, 'number_of_replicas': 0}

    class Django:
        model = User
        fields = ['username']
