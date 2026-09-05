from django.urls import path

from titles.views import (ChartView, SearchTitleView, TitleDetailView,
                          TitleGeneratorView, set_status)

app_name = 'titles'

urlpatterns = [
    path('title_generator/', TitleGeneratorView.as_view(), name='title_generator'),
    path('<str:type>/<int:title_id>/', TitleDetailView.as_view(), name='title_page'),
    path('ajax/search/', SearchTitleView.as_view(), name='search'),
    path('ajax/chart/<str:type>/', ChartView.as_view(), name='chart'),
    path('ajax/<int:title_id>/set_status/<str:status>/', set_status, name='set_status'),
]
