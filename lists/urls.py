from django.urls import path

from lists.views import (
    CollectionListView,
    FolderDeleteView,
    FolderFormView,
    FolderListView,
    get_collections_ajax,
    get_folders,
    toggle_folder_title,
)

app_name = 'lists'

urlpatterns = [
    path('ajax/get_collections/', get_collections_ajax, name='get_collections_ajax'),
    path('ajax/get_folders/member/<int:title_id>', get_folders, name='get_folders'),
    path('ajax/folder/<int:folder_id>/title/<int:title_id>/', toggle_folder_title, name='toggle_folder_title'),
    path('ajax/folder_form/', FolderFormView.as_view(), name='folder_form'),
    path('folder/<int:folder_id>/', FolderListView.as_view(), name='folder'),
    path('folder/<int:folder_id>/delete/', FolderDeleteView.as_view(), name='delete_folder'),
    path('folder/<int:folder_id>/<path:path_params>/', FolderListView.as_view(), name='folder'),
    path('', CollectionListView.as_view(), name='collection'),
    path('<path:path_params>/', CollectionListView.as_view(), name='collection'),
]
