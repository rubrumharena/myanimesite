from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

from .models import Title


@registry.register_document
class TitleDocument(Document):
    name = fields.TextField(analyzer='russian')
    names = fields.TextField(multi=True)

    class Index:
        name = 'title'
        settings = {'number_of_shards': 1, 'number_of_replicas': 0}

    class Django:
        model = Title
        fields = ['alternative_name']

    def prepare_names(self, instance):
        return instance.names or []
