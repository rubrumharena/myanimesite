from django.urls import path

from lists.views import (
    CollectionListView,
    FolderDeleteView,
    FolderListView,
    get_collections_ajax,
    get_user_folders_ajax,
    get_user_titles_ajax,
    save_folder_ajax,
    update_folder_titles_ajax,
)

app_name = 'lists'

urlpatterns = [
    path('ajax/get_collections/', get_collections_ajax, name='get_collections_ajax'),
    path('ajax/get_user_folders/', get_user_folders_ajax, name='get_user_folders_ajax'),
    path('ajax/update_folder_titles/', update_folder_titles_ajax, name='update_folder_titles_ajax'),
    path('ajax/save_folder/', save_folder_ajax, name='save_folder_ajax'),
    path('ajax/get_user_titles/', get_user_titles_ajax, name='get_user_titles_ajax'),
    path('folder/<int:folder_id>/', FolderListView.as_view(), name='folder'),
    path('folder/<int:folder_id>/delete/', FolderDeleteView.as_view(), name='delete_folder'),
    path('folder/<int:folder_id>/<path:path_params>/', FolderListView.as_view(), name='folder'),
    path('', CollectionListView.as_view(), name='collection'),
    path('<path:path_params>/', CollectionListView.as_view(), name='collection'),
]
