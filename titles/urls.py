from django.urls import path

from titles.views import TitleDetailView, bulk_title_generator_view, get_chart_ajax, search_ajax, set_rating_ajax

app_name = 'titles'

urlpatterns = [
    path('title_generator/', bulk_title_generator_view, name='title_generator'),
    path('<str:type>/<int:title_id>/', TitleDetailView.as_view(), name='title_page'),
    path('ajax/search/', search_ajax, name='search_ajax'),
    path('ajax/set_rating/', set_rating_ajax, name='set_rating_ajax'),
    path('ajax/get_chart/', get_chart_ajax, name='get_chart_ajax'),
]
