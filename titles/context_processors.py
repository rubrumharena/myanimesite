from lists.models import Folder


def user_library(request):
    user = request.user
    return {
        'user_library': list(
            Folder.titles.through.objects.filter(folder__user=user).values_list('title_id', flat=True).distinct()
        )
        if user.is_authenticated
        else []
    }
