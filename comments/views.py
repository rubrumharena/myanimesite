from functools import cached_property
from http import HTTPStatus

from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, reverse
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.views.generic import ListView, TemplateView

from comments.forms import CommentForm, ReviewForm
from comments.models import Comment, CommentLikeHistory
from common.utils.cache_keys import CommentsCacheKey, cache_by_func
from common.utils.enums import CommentType
from common.utils.wrappers import login_required_ajax
from common.views.bases import BaseCommentFormView
from common.views.mixins import PaginatorMixin
from lists.models import Collection
from titles.models import LibraryEntry, Title
from users.models import User

# Create your views here.


class CommentListView(PaginatorMixin, ListView):
    model = Comment
    template_name = 'comments/comment_tree.html'
    paginate_by = 24
    form_prefix = 'comment'

    def build_comment_tree(self, root_comments):
        title_id = self.kwargs.get('title_id')
        root_ids = [c.id for c in root_comments]
        comments = (
            self.model.objects.filter(title=title_id, parent_id__in=root_ids)
            .order_by('-created_at')
            .select_related('user')
        )
        comment_tree = {root_id: [] for root_id in root_ids}
        for comment in comments:
            comment_tree[comment.parent_id].append(comment)

        return comment_tree

    def build_comment_root(self):
        filter_by = self.request.GET.get('filter_by')
        title_id = self.kwargs.get('title_id')

        if filter_by == CommentType.REVIEWS.value:
            f = {'review__isnull': False}
        elif filter_by == CommentType.FEEDBACKS.value:
            f = {'review__isnull': True}
        else:
            f = {}

        queryset = (
            super()
            .get_queryset()
            .filter(title_id=title_id, parent__isnull=True, **f)
            .order_by('-created_at')
            .select_related('user')
        )
        return queryset

    def get_queryset(self):
        filter_by = self.request.GET.get('filter_by')
        title_id = self.kwargs.get('title_id')
        cache_key = CommentsCacheKey.root_comments(title_id, filter_by)
        return cache_by_func(lambda: self.build_comment_root(), cache_key)

    def render_to_response(self, context, **response_kwargs):
        html = render_to_string(self.template_name, context, request=self.request)
        return JsonResponse(
            {'html': html}, status=response_kwargs.get('status', response_kwargs.get('status', HTTPStatus.OK))
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        title_id = self.kwargs.get('title_id')
        user = self.request.user
        form = kwargs.get(
            'form',
            CommentForm(prefix=self.form_prefix),
        )
        context['form'] = form
        context['title_id'] = title_id
        if form.errors:
            context.update(
                {
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

        cache_key = CommentsCacheKey.comment_tree(title_id)
        comment_tree = cache_by_func(lambda: self.build_comment_tree(root_comments), cache_key)

        return {**context, 'tree': comment_tree, 'root': root_comments, 'liked_comments': liked_by_user}

    @method_decorator(login_required_ajax)
    def post(self, request, *args, **kwargs):
        data = request.POST
        comment_id = data.get(f'{self.form_prefix}-comment_id')
        title_id = self.kwargs.get('title_id')
        instance = None

        if comment_id:
            instance = get_object_or_404(
                Comment,
                id=comment_id,
                user=request.user,
                title_id=self.kwargs['title_id'],
            )

        form = CommentForm(
            prefix=self.form_prefix, data=data, user_id=request.user.id, title_id=title_id, instance=instance
        )

        if form.is_valid():
            comment = form.save()
            return JsonResponse(data={'commentId': comment.id}, status=HTTPStatus.OK)

        self.object_list = self.get_queryset()
        return self.render_to_response(self.get_context_data(form=form), status=HTTPStatus.BAD_REQUEST)


class PreviewTemplateView(TemplateView):
    template_name = 'comments/modals/preview.html'

    def dispatch(self, request, *args, **kwargs):
        user = get_object_or_404(User, id=self.kwargs['user_id'])
        if user.is_hidden and self.request.user != user:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def render_to_response(self, context, **response_kwargs):
        html = render_to_string(self.template_name, context, request=self.request)
        return JsonResponse(
            {'html': html}, status=response_kwargs.get('status', response_kwargs.get('status', HTTPStatus.OK))
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        title_id, user_id = self.kwargs['title_id'], self.kwargs['user_id']

        review = get_object_or_404(
            LibraryEntry.objects.select_related('title__poster', 'user', 'entry').prefetch_related(
                Prefetch(
                    'title__collection_titles',
                    queryset=Collection.objects.filter(type=Collection.GENRE),
                    to_attr='genres',
                )
            ),
            title_id=title_id,
            user_id=user_id,
        )

        return {
            **context,
            'comment': getattr(review, 'entry', {}),
            'review': review,
            'title': review.title,
            'owner': review.user,
        }


class ReviewFormView(BaseCommentFormView):
    template_name = 'comments/modals/review_edit.html'
    form_class = ReviewForm

    @cached_property
    def instance(self):
        return Comment.objects.filter(
            title_id=self.kwargs['title_id'], user=self.request.user, review__isnull=False
        ).first()

    def get_prefix(self):
        return 'review'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        kwargs['user_id'] = self.request.user.id
        kwargs['title_id'] = self.kwargs['title_id']

        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        if self.instance:
            initial['status'] = self.instance.review.status or LibraryEntry.NOT_WATCHED
            initial['rating'] = self.instance.review.rating
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = kwargs.get('form') or self.get_form()
        context['title'] = get_object_or_404(Title, id=self.kwargs['title_id'])

        context['review'] = context['form'].instance.review
        return context


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


@require_POST
@login_required_ajax
def delete_comment(request, comment_id):
    comment = Comment.objects.filter(id=comment_id, user=request.user).first()
    if comment:
        comment.delete()
    return JsonResponse(data={}, status=HTTPStatus.OK)


@require_POST
@login_required
def delete_review(request, title_id):
    review = Comment.objects.filter(title_id=title_id, user_id=request.user.id, review__isnull=False).first()
    if review:
        review.delete()
    return HttpResponseRedirect(reverse('users:profile', kwargs={'username': request.user.username}))
