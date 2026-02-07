import json

from django.contrib.auth import get_user_model
from django.db.models import Q, F, Count, ExpressionWrapper, OuterRef, Subquery, Func, FloatField
from django.db.models.functions import Extract, Round
from django.http import JsonResponse
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action, api_view
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError
from rest_framework.filters import OrderingFilter

from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import mixins, status, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticatedOrReadOnly, BasePermission, IsAuthenticated, SAFE_METHODS
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.viewsets import GenericViewSet

from notifications.signals import notify

# from alpha_minio.alpha_minio_worker import alpha_mimio
from voting.models import Vote

from complaints.models import Complaint
from favorite.models import Favorite
from users.models import Subscription
from utils.search_mixin import SearchMixin
from .filters import TopicFilter, MembershipFilter
from .models import Category, Comment, Topic, Image, LastTopicCommentRead, ForumRules, Membership
from .permissions import ImageCanDelete, IsAuthorOrIsAdminOrCreateReadOnly, IsAuthor
from .serializers import (
    CategorySerializer,
    CommentSerializer,
    # TopicCreateSerializer,
    # TopicListSerializer,
    TopicSerializer,
    ImageSerializer, MembershipSerializer, TopicListSerializer,
)

User = get_user_model()


class ForumPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 150


# # FIXME describe why is this is needed?
# class GetObjectMixIn:
#     def get_object(self):
#         queryset = self.filter_queryset(self.get_queryset())
#
#         # Perform the lookup filtering.
#         lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
#
#         assert lookup_url_kwarg in self.kwargs, (
#                 "Expected view %s to be called with a URL keyword argument "
#                 'named "%s". Fix your URL conf, or set the `.lookup_field` '
#                 "attribute on the view correctly."
#                 % (self.__class__.__name__, lookup_url_kwarg)
#         )
#
#         filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
#
#         if self.action not in ("retrieve", "list"):
#             filter_kwargs.update({"user": self.request.user})
#         obj = get_object_or_404(queryset, **filter_kwargs)
#
#         self.check_object_permissions(self.request, obj)
#
#         return obj


class CategoryViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ("parent", "order")

    def get_queryset(self):
        qs = super().get_queryset()
        topics_to_count = Topic.objects.filter(published_at__isnull=False).filter(
            Q(category=OuterRef('pk')) | Q(category__parent=OuterRef('pk'))).order_by().annotate(
            count=Func(F('id'), function='Count')
        ).values('count')

        qs = qs.annotate(topics_count=Subquery(topics_to_count))

        return qs


class TopicViewSet(mixins.CreateModelMixin,
                   mixins.RetrieveModelMixin,
                   mixins.UpdateModelMixin,
                   mixins.DestroyModelMixin,
                   mixins.ListModelMixin,
                   GenericViewSet,
                   SearchMixin
                   ):
    # permission_classes = (IsAuthorOrIsAdminOrCreateReadOnly,)
    # permission_classes = (IsAuthenticated, IsAuthorOrIsAdminOrCreateReadOnly,)
    queryset = Topic.objects.all().prefetch_related("comments", "images__creator", "membership_set__user",
                                                    "membership_set__inviter",
                                                    "user_unread_count").select_related(
        "user__profile", "category").order_by("-updated_at")
    serializer_class = TopicSerializer
    # filter_backends = (DjangoFilterBackend, OrderingFilter)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = TopicFilter
    pagination_class = ForumPagination
    search_weights_fields = [["title", "A"], ["description", "B"]]

    # this will product duplicate, see for details https://stackoverflow.com/a/63999236/1271271
    # , ["category__title", "A"], ["comments__text", "D"]] this
    # search_fields = ['title', 'description', 'category__title', 'comments__text']

    def get_object(self):
        # ===== copy paste from parent class
        queryset = self.filter_queryset(self.get_queryset())

        # add own filter
        if self.request.user.is_authenticated:
            # filter for auth users
            queryset = queryset.filter(
                (Q(access_level=Topic.AccessLevel.PUBLIC.value) & Q(published_at__isnull=False) & Q(
                    status__in=["not_checked", "accepted"]))  # public topic
                | Q(user=self.request.user)  # topic creator
                | (Q(membership__user__in=(self.request.user,)) & Q(
                    membership__status__in=["accepted", ])) & Q(
                    status__in=["not_checked", "accepted"]))  # private topic
        else:
            # anon user
            queryset = queryset.filter(access_level=Topic.AccessLevel.PUBLIC.value, published_at__isnull=False,
                                       status__in=["not_checked", "accepted"])

        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        assert lookup_url_kwarg in self.kwargs, (
                'Expected view %s to be called with a URL keyword argument '
                'named "%s". Fix your URL conf, or set the `.lookup_field` '
                'attribute on the view correctly.' %
                (self.__class__.__name__, lookup_url_kwarg)
        )

        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        obj = get_object_or_404(queryset, **filter_kwargs)

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj

    def get_queryset(self):
        membership_to_count = Membership.objects.filter(
            topic=OuterRef('pk'), status=Membership.Status.ACCEPTED, user_status=Membership.UserStatus.ACCEPTED) \
            .order_by().annotate(count=Func(F('id'), function='Count')
                                 ).values('count')

        queryset = super().get_queryset() \
            .annotate(
            created_at_numeric=Extract('created_at', 'epoch')
        ).annotate(
            popular_weight=ExpressionWrapper(Count('comments') * F('created_at_numeric') / 1000000000,
                                             output_field=FloatField())). \
            annotate(count_of_members=Subquery(membership_to_count))

        return self.get_basic_filter_qs(queryset)

    def get_basic_filter_qs(self, queryset):
        # external function
        if self.request.user.is_authenticated:
            # filter for auth users
            queryset = queryset.filter(
                # (Q(access_level=Topic.AccessLevel.PUBLIC.value) & Q(published_at__isnull=False) & Q(
                (Q(published_at__isnull=False) & Q(
                    status__in=["not_checked", "accepted"]))  # public topic
                | Q(user=self.request.user))  # topic creator
            # | (Q(membership__user__in=(self.request.user,)) & Q(
            #     membership__status__in=["accepted", ])) & Q(
            #     status__in=["not_checked", "accepted"]))  # private topic
        else:
            # anon user
            queryset = queryset.filter(access_level=Topic.AccessLevel.PUBLIC.value, published_at__isnull=False,
                                       status__in=["not_checked", "accepted"])

        return queryset

    def get_throttles(self):
        if self.action in ['join']:
            self.throttle_scope = 'forum.' + self.action
        return super().get_throttles()

    def get_serializer_class(self):
        if self.action in ("list", "search"):
            return TopicListSerializer
        else:
            return super().get_serializer_class()

    @action(methods=['post'], detail=True, url_path="like", permission_classes=[IsAuthenticated, ])
    def like(self, request, *args, **kwargs):
        topic = self.get_object()
        vote = Vote.objects.get_for_user(topic, request.user)
        new_vote = 1
        if vote and vote.vote == 1:
            new_vote = 0  # remove vote
        Vote.objects.record_vote(topic, request.user, new_vote)
        return JsonResponse(data={"likes_count": Vote.objects.get_score(topic)["score"]}, status=status.HTTP_200_OK)

    @action(methods=['post'], detail=True, url_path="favorite", permission_classes=[IsAuthenticated, ])
    def favorite(self, request, *args, **kwargs):
        topic = self.get_object()
        try:
            favorite = Favorite.objects.get(topic=topic, author=request.user)
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Favorite.DoesNotExist:
            f = Favorite(content_object=topic, author=request.user)
            f.save()
            return Response(status=status.HTTP_201_CREATED)

    @action(methods=['post'], detail=False, url_path="join", permission_classes=[IsAuthenticated, ])
    def join(self, request, *args, **kwargs):
        # can't use this, due object is not accessible to external user
        # topic = self.get_object()

        try:
            topic = Topic.objects.get(pk=request.data.get("topic_id", None))
        except Topic.DoesNotExist:
            raise NotFound()

        member_status = Membership.Status.NEW
        if topic.access_level == topic.AccessLevel.PUBLIC:
            # for public auto accepted (for admin)
            member_status = Membership.Status.ACCEPTED

        try:
            member = Membership.objects.get(topic=topic, user=request.user)
            member.status = member_status
            member.user_status = Membership.UserStatus.ACCEPTED
            member.save()
        except Membership.DoesNotExist:
            Membership.objects.create(topic=topic, user=request.user, status=member_status,
                                      user_status=Membership.UserStatus.ACCEPTED, inviter=request.user)
            # send notification for the new one join
            # request.user (actor) - requested to join topic (verb) - author (action_object) - topic (target)
            # notify.send(actor, recipient, verb, action_object, target, level, description, public, timestamp, **kwargs)
            if topic.access_level == topic.AccessLevel.PRIVATE:
                notify.send(request.user, recipient=topic.user, action_object=topic.user, target=topic,
                            verb='requested to join topic')

        return Response(status=status.HTTP_201_CREATED)

    @action(methods=['post'], detail=True, url_path="accept", permission_classes=[IsAuthenticated, ])
    def accept(self, request, *args, **kwargs):
        topic = self.get_object()

        try:
            member = Membership.objects.get(topic=topic, user=request.user)
            member.user_status = Membership.UserStatus.ACCEPTED
            member.save()
        except Membership.DoesNotExist:
            raise NotFound()

        return Response(status=status.HTTP_201_CREATED)

    @action(methods=['post'], detail=True, url_path="accept", permission_classes=[IsAuthenticated, ])
    def reject(self, request, *args, **kwargs):
        topic = self.get_object()

        try:
            member = Membership.objects.get(topic=topic, user=request.user)
            member.user_status = Membership.UserStatus.REJECTED
            member.save()
        except Membership.DoesNotExist:
            raise NotFound()

        return Response(status=status.HTTP_201_CREATED)

    @action(methods=['post'], detail=True, url_path="archive", permission_classes=[IsAuthenticated, ])
    def archive(self, request, *args, **kwargs):
        topic = self.get_object()

        if not (request.user.is_superuser or request.user.is_staff):
            if topic.user != request.user:
                raise PermissionDenied("You do not have rights to archive the topic")

        topic.status = Topic.Status.ARCHIVE
        topic.published_at = None
        topic.save()

        return Response(status=status.HTTP_201_CREATED, data=TopicSerializer(instance=topic).data)

    @action(methods=['post'], detail=True, url_path="archive-restore", permission_classes=[IsAuthenticated, ])
    def archive_restore(self, request, *args, **kwargs):
        topic = self.get_object()

        if not (request.user.is_superuser or request.user.is_staff):
            if topic.user != request.user:
                raise PermissionDenied("You do not have rights to archive-restore the topic")

        topic.status = Topic.Status.NOT_CHECKED
        topic.save()

        return Response(status=status.HTTP_201_CREATED, data=TopicSerializer(instance=topic).data)

    @action(methods=['post'], detail=True, url_path="leave", permission_classes=[IsAuthenticated, ])
    def leave(self, request, *args, **kwargs):
        topic = self.get_object()
        try:
            topic.membership_set.get(user=request.user).delete()
        except Membership.DoesNotExist:
            raise NotFound()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['post'], detail=True, url_path="remove", permission_classes=[IsAuthor, ])
    def remove(self, request, *args, **kwargs):
        """
        remove user from topic, {"user": {id}} required
        """
        topic = self.get_object()

        user_id = request.data.get('user', None)
        if not user_id:
            raise ValidationError("Please, provide user id")

        try:
            topic.membership_set.get(user=user_id).delete()
        except Membership.DoesNotExist:
            raise NotFound()

        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_create(self, serializer):
        topic = serializer.save(user=self.request.user)
        if not topic.published_at:
            return

        subscribers = User.objects.filter(id__in=Subscription.objects.filter(user_dst=self.request.user).
                                          values_list('user_src', flat=True).distinct())
        if subscribers:
            notify.send(self.request.user, recipient=subscribers, action_object=topic, verb='new topic', target=topic)

    def perform_update(self, serializer):
        # don't forget to remove moderated_at at update
        if (
                serializer.validated_data.get('published_at', None) is None
                or Topic.objects.get(pk=serializer.instance.pk).published_at is not None
        ):
            # if the topic is not yet published or has already been published
            serializer.save(moderated_at=None)
            return

        topic = serializer.save(moderated_at=None)
        subscribers = User.objects.filter(id__in=Subscription.objects.filter(user_dst=self.request.user).
                                          values_list('user_src', flat=True).distinct())
        if subscribers:
            notify.send(self.request.user, recipient=subscribers, action_object=topic, verb='new topic', target=topic)

    # Destroy change status. No so good it can be suddenly removed


class IsAuthorTopic(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.topic.user == request.user

    # # we need to make user request
    # def has_permission(self, request, view):
    #     if request.method == 'POST':
    #         topic = request.data.get('topic', 0)
    #         try:
    #             topic = Topic.objects.get(pk=topic)
    #             return topic.user == request.user
    #         except Topic.DoesNotExist:
    #             return False
    #     return True


class TopicMembersViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin,
                          viewsets.GenericViewSet):
    permission_classes = (IsAuthenticated, IsAuthorTopic)
    queryset = Membership.objects.all().select_related("topic", "user__profile", "inviter__profile")
    serializer_class = MembershipSerializer
    filter_backends = (DjangoFilterBackend,)
    # filterset_fields = ("topic", "user", "status")
    filterset_class = MembershipFilter

    def get_throttles(self):
        if self.action in ['create']:
            self.throttle_scope = 'memebership.' + self.action
        return super().get_throttles()

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(Q(Q(status=Membership.Status.ACCEPTED) & Q(
            user_status=Membership.UserStatus.ACCEPTED))  # only accepted (public info)
                       | Q(topic__user=self.request.user)  # topic creator
                       | Q(user=self.request.user)  # user invited
                       )
        return qs

    def perform_create(self, serializer):
        # make status default
        topic = serializer.validated_data.get("topic")
        # validate that topic is not blocked
        if topic.status in [Topic.Status.BLOCKED, Topic.Status.TEMPORARY_BLOCKED]:
            raise ValidationError("Topic is blocked")

        # check access
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            # check user in subscriptions
            user_invited = serializer.validated_data.get("user", None)
            if Subscription.objects.filter(user_dst=self.request.user, user_src=user_invited, status=1).count() == 0:
                raise ValidationError({"user_id": "You can't invite users not from your subscriptions"})

        # created by admin
        member_status = Membership.Status.ACCEPTED
        # if topic.access_level == Topic.AccessLevel.PUBLIC:
        #     member_status = Membership.Status.ACCEPTED
        member = serializer.save(inviter=self.request.user, status=member_status, user_status=Membership.UserStatus.NEW)

        # send notification
        # Author (actor) - invite to topic (verb) - invited (action_object) - topic (target)
        # notify.send(actor, recipient, verb, action_object, target, level, description, public, timestamp, **kwargs)
        if topic.published_at:
            notify.send(topic.user, recipient=member.user, action_object=member.user, target=topic,
                        verb='invite to topic')

    def perform_update(self, serializer):
        member = serializer.save()
        if member.status == Membership.Status.ACCEPTED:
            # Author approved user
            if member.topic.published_at:
                # Author (actor) - accepted to topic (verb) - invited (action_object) - topic (target)
                notify.send(member.topic.user, recipient=member.user, action_object=member.user, target=member.topic,
                            verb='accepted to topic')


class CommentViewSet(
    # GetObjectMixIn,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    # permission_classes = [IsAuthorOrIsAdminOrCreateReadOnly]
    permission_classes = [IsAuthenticated, IsAuthorOrIsAdminOrCreateReadOnly]

    queryset = Comment.objects.all().select_related("user__profile", "comment__user__profile", "image",
                                                    "topic").distinct()
    serializer_class = CommentSerializer
    pagination_class = ForumPagination
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_fields = ("topic", "user")
    ordering_fields = ['created_at', 'updated_at']

    @action(methods=['post'], detail=True, url_path="like", permission_classes=[IsAuthenticated, ])
    def like(self, request, *args, **kwargs):
        comment = self.get_object()
        vote = Vote.objects.get_for_user(comment, request.user)
        new_vote = 1
        if vote and vote.vote == 1:
            new_vote = 0  # remove vote
        Vote.objects.record_vote(comment, request.user, new_vote)
        return JsonResponse(data={"likes_count": Vote.objects.get_score(comment)["score"]}, status=status.HTTP_200_OK)

    @action(methods=['post'], detail=True, url_path="complaint", permission_classes=[IsAuthenticated, ])
    def complaint(self, request, *args, **kwargs):
        details = request.data.get("details", "")
        c = Complaint(content_object=self.get_object(), user=request.user, details=details)
        c.save()
        return JsonResponse(data={}, status=status.HTTP_200_OK)

    @action(methods=['post'], detail=True, url_path="set-last-read")
    def set_last_read(self, request, *args, **kwargs):
        comment = self.get_object()
        try:
            last = LastTopicCommentRead.objects.get(user=request.user, topic=comment.topic)
            last.last_user_comment_seen = comment
            last.save()
        except LastTopicCommentRead.DoesNotExist:
            LastTopicCommentRead.objects.create(user=request.user, topic=comment.topic, last_user_comment_seen=comment)

        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_create(self, serializer):
        topic = serializer.validated_data.get('topic')
        parent_comment = serializer.validated_data.get('comment', None)
        # replace stop words
        from stop_words.service import replace_stop_words
        text = replace_stop_words(serializer.validated_data.get("text", ""))
        comment = serializer.save(user=self.request.user, text=text)
        # send notification to author of parent comment
        if parent_comment and self.request.user != parent_comment.user:
            notify.send(self.request.user, recipient=parent_comment.user, target=parent_comment, action_object=comment,
                        verb='reply to comment', description=text)
        # send notification to author of topic
        if (
                (not parent_comment or parent_comment.user != topic.user)
                and self.request.user != topic.user
                and topic.user.id != settings.SCHOOL_USER_ID
        ):
            notify.send(self.request.user, recipient=topic.user, target=topic, action_object=comment,
                        verb='comment in topic', description=text)

    def perform_update(self, serializer):
        # replace stop words
        from stop_words.service import replace_stop_words
        text = replace_stop_words(serializer.validated_data.get("text", ""))
        serializer.save(user=self.request.user, text=text)

    def get_queryset(self):
        qs = super().get_queryset()

        # this filters the same as in TOPIC!
        if self.request.user.is_authenticated:
            return qs.filter(
                (Q(topic__access_level=Topic.AccessLevel.PUBLIC.value) & Q(topic__published_at__isnull=False) & Q(
                    topic__status__in=["not_checked", "accepted"]))  # public topic
                | Q(topic__user=self.request.user)  # topic creator
                | (Q(topic__membership__user__in=(self.request.user,)) & Q(
                    topic__membership__status__in=["accepted", ])) & Q(
                    topic__status__in=["not_checked", "accepted"]))  # private topic
        else:
            # anon user
            return qs.filter(topic__access_level=Topic.AccessLevel.PUBLIC.value, topic__published_at__isnull=False,
                             topic__status__in=["not_checked", "accepted"])


class ImageViewSet(mixins.CreateModelMixin,
                   mixins.RetrieveModelMixin,
                   mixins.DestroyModelMixin,
                   mixins.ListModelMixin,
                   GenericViewSet):
    throttle_classes = [UserRateThrottle]  # 'user': '1000/day' by default
    queryset = Image.objects.order_by('-created_at')
    serializer_class = ImageSerializer
    parser_classes = (MultiPartParser, FormParser)
    # permission_classes = [IsAuthenticatedOrReadOnly, ImageCanDelete]
    permission_classes = [IsAuthenticated, ImageCanDelete]
    pagination_class = ForumPagination

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)


@api_view(['GET'])
def get_forum_rules(request):
    rules = ForumRules.objects.filter(published_at__isnull=False).last()
    if rules:
        return Response({"title": rules.title, "description": rules.description})
    else:
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
def get_topic_info(request, id, *args, **kwargs):
    try:
        topic = Topic.objects.get(pk=id)

        return JsonResponse(data=TopicSerializer(instance=topic).data, status=status.HTTP_200_OK)
    except Topic.DoesNotExist:
        return Response(status=status.HTTP_204_NO_CONTENT)