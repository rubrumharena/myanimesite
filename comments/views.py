from functools import cached_property
from http import HTTPStatus

from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.views.generic import ListView

from comments.forms import CommentForm
from comments.models import Comment, CommentLikeHistory
from common.utils.cache_keys import CommentsCacheKey, TitlesCacheKey
from common.utils.wrappers import login_required_ajax
from common.views.mixins import PaginatorMixin
from titles.models import Title

# Create your views here.


class CommentListView(PaginatorMixin, ListView):
    model = Comment
    template_name = 'comments/comment_tree.html'
    paginate_by = 24

    @cached_property
    def title(self):
        title_id = self.kwargs.get('title_id')
        cache_key = TitlesCacheKey.title(title_id)
        title = cache.get(cache_key)
        if title is not None:
            return title

        title = get_object_or_404(Title, id=title_id)
        cache.set(cache_key, title, 60**2 * 24)
        return title

    def get_queryset(self):
        title_id = self.title.id
        cache_key = CommentsCacheKey.root_comments(title_id)
        queryset = cache.get(cache_key)
        if queryset is not None:
            return queryset
        queryset = (
            super()
            .get_queryset()
            .filter(title_id=title_id, parent__isnull=True)
            .order_by('-created_at')
            .select_related('user')
        )
        cache.set(cache_key, queryset, 30)
        return queryset

    def render_to_response(self, context, **response_kwargs):
        html = render_to_string(self.template_name, context, request=self.request)
        return JsonResponse({'html': html}, status=response_kwargs.get('status', HTTPStatus.OK))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        form = kwargs.get('form', CommentForm())

        base_context = {'form': form, 'title': self.title}

        if form.errors:
            context.update(
                {
                    **base_context,
                    'tree': {},
                    'root': [],
                    'liked_comments': [],
                }
            )
            return context

        root_comments = context.get('object_list', [])
        liked_by_user = (
            CommentLikeHistory.objects.filter(user=user).values_list('comment_id', flat=True)
            if user.is_authenticated
            else []
        )

        cache_key = CommentsCacheKey.comment_tree(self.title.id)
        comment_tree = cache.get(cache_key)
        if comment_tree is None:
            comments = self.model.objects.filter(title=self.title).order_by('-created_at').select_related('user')
            comment_tree = {comment.id: [] for comment in comments}

            for comment in comments:
                parent_id = comment.parent_id
                if parent_id:
                    comment_tree[parent_id].append(comment)
            cache.set(cache_key, comment_tree, 30)

        return {**context, **base_context, 'tree': comment_tree, 'root': root_comments, 'liked_comments': liked_by_user}

    @method_decorator(login_required_ajax)
    def post(self, request, *args, **kwargs):
        data = request.POST
        form = CommentForm(data=data, request=request, title=self.title)

        if form.is_valid():
            form.save()
            return JsonResponse({}, status=HTTPStatus.OK)

        self.object_list = self.get_queryset()
        return self.render_to_response(self.get_context_data(form=form), status=HTTPStatus.BAD_REQUEST)


@require_POST
@login_required_ajax
def like_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)

    like_obj, is_created = CommentLikeHistory.objects.get_or_create(user=request.user, comment_id=comment_id)

    if is_created:
        comment.like_count += 1
    else:
        like_obj.delete()
        comment.like_count -= 1

    comment.save()
    return JsonResponse(data={'likeCount': comment.like_count}, status=HTTPStatus.OK)
