from django.urls import path

from titles.views import ChartView, SearchTitleView, TitleDetailView, TitleGeneratorView, set_rating

app_name = 'titles'

urlpatterns = [
    path('title_generator/', TitleGeneratorView.as_view(), name='title_generator'),
    path('<str:type>/<int:title_id>/', TitleDetailView.as_view(), name='title_page'),
    path('ajax/search/', SearchTitleView.as_view(), name='search'),
    path('ajax/chart/<str:type>/', ChartView.as_view(), name='chart'),
    path('ajax/<int:title_id>/set_rating/<int:rating>/', set_rating, name='set_rating'),
]
