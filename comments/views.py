from http import HTTPStatus

from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_POST

from comments.forms import CommentForm
from comments.models import Comment, CommentLikeHistory
from common.utils.humanizers import humanize_date_time
from common.utils.wrappers import login_required_ajax
from titles.models import Title

# Create your views here.


class CommentAjaxView(View):
    paginate_by = 24

    def _serialize_page_data(self, queryset):
        paginator = Paginator(queryset, self.paginate_by)

        page = int(self.request.GET.get('page', 1))
        if paginator.num_pages < page or page <= 0:
            raise ValueError

        page_obj = paginator.get_page(page)
        has_previous = page_obj.has_previous()
        has_next = page_obj.has_next()

        return {
            'page_obj': {
                'has_previous': has_previous,
                'has_next': has_next,
                'previous_page_number': page_obj.previous_page_number() if has_previous else None,
                'next_page_number': page_obj.next_page_number() if has_next else None,
                'number': page_obj.number,
                'object_list': page_obj.object_list,
            },
            'page_range': list(paginator.get_elided_page_range(number=page, on_each_side=2, on_ends=1)),
            'ellipsis': page_obj.paginator.ELLIPSIS,
        }

    def get(self, request, *args, **kwargs):
        title = get_object_or_404(Title, id=self.kwargs.get('title_id'))
        user = self.request.user
        liked_comments = (
            list(CommentLikeHistory.objects.filter(user=user).values_list('comment_id', flat=True))
            if user.is_authenticated
            else []
        )
        all_comments = (
            Comment.objects.filter(title=title)
            .order_by('-created_at')
            .values(
                'id', 'user__username', 'user__name', 'user__avatar', 'like_count', 'text', 'parent_id', 'created_at'
            )
        )
        comment_tree = {comment['id']: [] for comment in all_comments}

        stem_comments = []
        for comment in all_comments:
            date = comment['created_at']
            comment['created_at'] = humanize_date_time(date)
            comment['user_url'] = reverse('users:profile', kwargs={'username': comment['user__username']})
            comment['user__avatar'] = comment['user__avatar'].url if comment['user__avatar'] else None
            parent_id = comment['parent_id']

            if parent_id:
                comment_tree[parent_id].append(comment)
            else:
                stem_comments.append(comment)
        try:
            page_data = self._serialize_page_data(stem_comments)
        except (ValueError, TypeError):
            return JsonResponse({}, status=HTTPStatus.BAD_REQUEST)
        return JsonResponse(
            data={**page_data, 'comment_tree': comment_tree, 'liked_comments': liked_comments}, status=HTTPStatus.OK
        )

    @method_decorator(login_required_ajax)
    def post(self, request, *args, **kwargs):
        data = request.POST
        form = CommentForm(data=data, request=request)

        if form.is_valid():
            form.save()
            return JsonResponse(status=HTTPStatus.OK, data=data)

        return JsonResponse(status=HTTPStatus.BAD_REQUEST, data={'errors': form.errors})


@require_POST
@login_required_ajax
def like_comment_ajax(request):
    data = request.POST
    try:
        comment_id = int(data.get('comment_id'))
    except (TypeError, ValueError):
        return JsonResponse(data={}, status=HTTPStatus.BAD_REQUEST)
    comment = get_object_or_404(Comment, id=comment_id)

    like_obj, is_created = CommentLikeHistory.objects.get_or_create(user=request.user, comment_id=comment_id)

    if is_created:
        comment.like_count += 1
    else:
        like_obj.delete()
        comment.like_count -= 1

    comment.save()
    return JsonResponse(data={'like_count': comment.like_count}, status=HTTPStatus.OK)
