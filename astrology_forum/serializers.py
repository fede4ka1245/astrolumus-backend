from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils.timezone import now
from django.template.defaultfilters import truncatechars_html

from notifications.signals import notify

from rest_framework import serializers
from rest_framework.exceptions import ValidationError, NotAuthenticated, PermissionDenied
from rest_framework.relations import PrimaryKeyRelatedField
from voting.models import Vote

from favorite.models import Favorite
from users.serializers import PublicUserSimpleSerializer
from .models import Category, Comment, Topic, Image, LastTopicCommentRead, Membership

User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    topics_count = serializers.IntegerField()

    class Meta:
        model = Category
        fields = "__all__"


class ImageSerializer(serializers.ModelSerializer):
    creator = serializers.ReadOnlyField(source='creator.nickname')
    creator_id = serializers.ReadOnlyField(source='creator.id')
    image = serializers.ImageField(required=True)
    image_original = serializers.ImageField(required=True)

    class Meta:
        model = Image
        fields = ['id', 'creator', 'creator_id', 'created_at', 'updated_at', 'image', 'image_original']


class TopicListSerializer(serializers.ModelSerializer):
    current_user_unread = serializers.SerializerMethodField()
    current_user_liked = serializers.SerializerMethodField()
    current_user_favorite = serializers.SerializerMethodField()
    current_user_is_member = serializers.SerializerMethodField()
    current_user_sent_join = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    published_at = serializers.DateTimeField(allow_null=True)
    popular_weight = serializers.FloatField(read_only=True)
    count_of_members = serializers.IntegerField(read_only=True)
    category_title = serializers.CharField(source="category.title", read_only=True)

    user = PublicUserSimpleSerializer(read_only=True)
    limited_members = serializers.SerializerMethodField('get_limited_members')

    def get_limited_members(self, obj):
        # TODO optimize this / one sql query per object
        qs = obj.membership_set.select_related("user__profile", "inviter__profile").filter(
            status=Membership.Status.ACCEPTED, user_status=Membership.UserStatus.ACCEPTED)[:3]
        return MembershipSerializer(instance=qs, many=True).data

    def get_likes_count(self, obj):
        # TODO optimize this / one sql query per object
        return Vote.objects.get_score(obj)["score"]

    def get_current_user_liked(self, obj):
        if "request" in self.context and self.context["request"].user.is_authenticated:
            # TODO optimize this / one sql query per object
            vote = Vote.objects.get_for_user(obj, self.context["request"].user)
            if vote:
                return True
        return False

    def get_current_user_is_member(self, obj):
        if "request" in self.context and self.context["request"].user.is_authenticated:
            # TODO optimize this / one sql query per object
            membership = obj.membership_set.filter(user_id=self.context["request"].user,
                                                   status=Membership.Status.ACCEPTED,
                                                   user_status=Membership.UserStatus.ACCEPTED,
                                                   )
            if membership.count() > 0:
                return True
        return False

    def get_current_user_sent_join(self, obj):
        if "request" in self.context and self.context["request"].user.is_authenticated:
            # TODO optimize this / one sql query per object
            membership = obj.membership_set.filter(user_id=self.context["request"].user,
                                                   status=Membership.Status.NEW,
                                                   user_status=Membership.UserStatus.ACCEPTED,
                                                   )
            if membership.count() > 0:
                return True
        return False

    def get_current_user_favorite(self, obj):
        if "request" in self.context and self.context["request"].user.is_authenticated:
            # TODO optimize this / one sql query per object
            try:
                Favorite.objects.get(topic=obj, author=self.context["request"].user)
                return True
            except Favorite.DoesNotExist:
                pass
        return False

    def get_current_user_unread(self, obj):
        if "request" in self.context and self.context["request"].user.is_authenticated:
            try:
                # TODO optimize this / one sql query per object / add annotate to get_queryset in the view
                last_read = obj.user_unread_count.get(user=self.context["request"].user, topic=obj)
                if last_read.last_user_comment_seen != obj.comments.last():
                    return True
            except LastTopicCommentRead.DoesNotExist:
                return True
        return False

    def to_representation(self, instance):
        ret = super(TopicListSerializer, self).to_representation(instance)
        if type(self) is TopicListSerializer:
            ret["description"] = truncatechars_html(instance.description, 150)
        return ret

    class Meta:
        model = Topic
        fields = (
            "id",
            "title",
            "description",
            "published_at",
            "created_at",
            "updated_at",
            "access_level",
            "category",
            "category_title",
            "popular_weight",
            "limited_members",
            "count_of_members",
            "user",
            "likes_count",
            "current_user_unread",
            "current_user_liked",
            "current_user_favorite",
            "current_user_is_member",
            "current_user_sent_join",
            "status"
        )
        read_only_fields = ('status',)
        extra_kwargs = {
            "title": {"required": False},
        }


class TopicSerializer(TopicListSerializer):
    comments_count = serializers.SerializerMethodField()
    images = ImageSerializer(many=True, read_only=True)
    images_ids = serializers.PrimaryKeyRelatedField(source="images", queryset=Image.objects.all(), many=True,
                                                    write_only=True, required=False)
    members_ids = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), many=True,
                                                     write_only=True, required=False)

    def create(self, validated_data):
        with transaction.atomic():
            members = validated_data.pop('members_ids', [])
            instance = super().create(validated_data)
            members_new = []
            for member in members:
                status = Membership.Status.NEW
                if instance.access_level == instance.AccessLevel.PUBLIC:
                    # for public auto accepted
                    status = Membership.Status.ACCEPTED

                members_new.append(
                    Membership(topic=instance, user=member, status=status, inviter=self.context["request"].user))

                # send notification
                # Author (actor) - invite to topic (verb) - invited (action_object) - topic (target)
                # notify.send(actor, recipient, verb, action_object, target, level, description, public, timestamp, **kwargs)
                if instance.published_at:
                    notify.send(instance.user, recipient=member, action_object=member, target=instance,
                                verb='invite to topic')

            if len(members_new) > 0:
                Membership.objects.bulk_create(members_new)
            return instance

    def update(self, instance, validated_data):
        with transaction.atomic():
            members = validated_data.pop('members_ids', [])
            instance = super().update(instance, validated_data)
            if len(members) > 0:
                members_new = []
                for member in members:
                    status = Membership.Status.NEW
                    if instance.access_level == instance.AccessLevel.PUBLIC:
                        # for public auto accepted
                        status = Membership.Status.ACCEPTED
                    # try to find existing
                    members_new.append(
                        Membership(topic=instance, user=member, status=status, inviter=self.context["request"].user))
                if len(members_new) > 0:
                    Membership.objects.bulk_create(members_new, update_conflicts=True,
                                                   unique_fields=["topic_id", "user_id"],
                                                   update_fields=["status"], )

                #  send user notification again if not was accepted
                for membership in Membership.objects.filter(topic=instance):
                    if membership.user_status != Membership.UserStatus.ACCEPTED:
                        notify.send(instance.user, recipient=member, action_object=member, target=instance,
                                    verb='invite to topic')
            return instance

    def get_comments_count(self, obj):
        return obj.comments.count()

    def validate_images_ids(self, value):
        if len(value) > 9:
            raise serializers.ValidationError("Can't set more than 9 images")
        return value

    def validate(self, data):
        if data.get("published_at", None):
            errors = {}
            if not data.get("description", None):
                errors["description"] = "Это поле обязательно"
            if not data.get("title", None):
                errors["title"] = "Это поле обязательно"
            if not data.get("category", None):
                errors["category"] = "Это поле обязательно"

            if errors:
                raise ValidationError(errors)
        else:
            if not data.get("title", None):
                data["title"] = f"Черновик от {now().strftime('%d.%m.%Y %H:%M')}"

        return data

    class Meta:
        model = Topic
        fields = (
            "id",
            "title",
            "description",
            "published_at",
            "created_at",
            "updated_at",
            "images",
            "images_ids",
            "access_level",
            "category",
            "category_title",
            "popular_weight",
            "members_ids",
            # "invited_ids",
            # "invited",
            "limited_members",
            "horoscope_link",
            "count_of_members",
            "user",
            "horoscope",
            "dim_sky",
            "comments_count",
            "likes_count",
            "current_user_unread",
            "current_user_liked",
            "current_user_favorite",
            "current_user_is_member",
            "status"
        )
        read_only_fields = ('status',)
        extra_kwargs = {
            "title": {"required": False, "allow_blank": True},
        }


class RecursiveField(serializers.BaseSerializer):
    def to_representation(self, value):
        depth = self.context.get('depth', 0)
        self.context['depth'] = depth + 1
        ParentSerializer = self.parent.__class__
        serializer = ParentSerializer(value, context=self.context, depth=self.context['depth'])

        return serializer.data

    def to_internal_value(self, data):
        ParentSerializer = self.parent.__class__
        Model = ParentSerializer.Meta.model
        try:
            instance = Model.objects.get(pk=data)
        except ObjectDoesNotExist:
            raise serializers.ValidationError(
                "Объект {0} не существует".format(
                    Model().__class__.__name__
                )
            )
        return instance


class CommentSerializer(serializers.ModelSerializer):
    image_id = serializers.PrimaryKeyRelatedField(source="image", queryset=Image.objects.all(), many=False,
                                                  write_only=True, required=False)
    image = ImageSerializer(many=False, read_only=True)
    user = PublicUserSimpleSerializer(read_only=True)
    likes_count = serializers.SerializerMethodField()
    current_user_liked = serializers.SerializerMethodField()
    topic_title = serializers.CharField(source="topic.title", read_only=True)
    comment_parent_page = serializers.SerializerMethodField()

    def __init__(self, *args, depth=0, **kwargs):
        super().__init__(*args, **kwargs)
        self.depth = depth

    def get_likes_count(self, obj):
        # TODO optimize this / one sql query per object
        return Vote.objects.get_score(obj)["score"]

    def get_comment_parent_page(self, obj):
        # TODO optimize this / one sql query per object
        # if it list query - get page of
        if self.depth == 0:
            if obj.comment and self.context['view'].action == 'list':
                queryset = self.context['view'].get_queryset()
                queryset = self.context['view'].filter_queryset(queryset)
                paginator = self.context['view'].paginator
                items_per_page = paginator.get_page_size(self.context['request'])
                kwargs = {}
                if queryset.query.order_by:
                    for order_by in queryset.query.order_by:
                        #     '-created_at'
                        if order_by[0] == "-":
                            kwargs[order_by[1:]+"__gt"] = getattr(obj.comment, order_by[1:])
                        else:
                            kwargs[order_by + "__lt"] = getattr(obj.comment, order_by)
                else:
                    # calculate by id
                    kwargs["pk__lt"] = obj.comment.pk

                count_before_parent = queryset.filter(**kwargs).count()
                page = count_before_parent // items_per_page + 1
                return page
        return None

    def get_current_user_liked(self, obj):
        if "request" in self.context and self.context["request"].user.is_authenticated:
            # TODO optimize this / one sql query per object
            vote = Vote.objects.get_for_user(obj, self.context["request"].user)
            if vote:
                return True
        return False

    def validate(self, data):
        # validate that topic is not blocked
        if data["topic"].status not in [Topic.Status.NOT_CHECKED, Topic.Status.ACCEPTED]:
            raise PermissionDenied("Topic is blocked or archived")

        # validate that topic has text or image ether
        if not data.get("text", None) and not data.get("image", None):
            raise ValidationError("Нужно добавить текст или изображение")

        # validate user took a part in members
        if "request" in self.context and self.context["request"].user.is_authenticated:
            current_user = self.context["request"].user
            if data["topic"].user != current_user:  # if not topic creator
                try:
                    Membership.objects.get(topic=data["topic"],
                                           user=current_user,
                                           status=Membership.Status.ACCEPTED,
                                           user_status=Membership.UserStatus.ACCEPTED,
                                           )
                except Membership.DoesNotExist:
                    raise PermissionDenied("You do not have permission to create comments in this topic")
        else:
            raise NotAuthenticated()

        # validate that parent comment is in the current topic due creation
        parent = data.get("comment", None)
        if parent:
            if parent.topic != data["topic"]:
                raise ValidationError("Parent comment not placed in selected topic")
        return data

    def to_representation(self, instance):
        ret = super(CommentSerializer, self).to_representation(instance)
        if instance.status == Comment.Status.BLOCKED:
            ret["text"] = ""
            ret["image"] = None
        return ret

    def get_fields(self):
        fields = super().get_fields()
        if self.depth == 0:
            fields['comment'] = RecursiveField(many=False, required=False)
        else:
            fields['comment'] = PrimaryKeyRelatedField(read_only=True)
        return fields

    class Meta:
        model = Comment
        fields = (
            "id",
            "topic",
            "topic_title",
            "text",
            "comment",
            "comment_parent_page",
            "image_id",
            "image",
            "created_at",
            "updated_at",
            "user",
            "likes_count",
            "current_user_liked",
            "status"
        )
        # extra_kwargs = {
        #     "text": {"required": True},
        # }
        read_only_fields = ('status',)


# class CommentToTopicSerializer(serializers.ModelSerializer):
#     def get_fields(self):
#         fields = super(CommentToTopicSerializer, self).get_fields()
#         fields["comment_comments"] = CommentToTopicSerializer(many=True)
#         return fields
#
#     def to_representation(self, instance):
#         data = super().to_representation(instance)
#         data["comments"] = data.pop("comment_comments")
#         return data
#
#     def validate(self, data):
#         if not data.get("topic") and not data.get("comment"):
#             raise serializers.ValidationError("You need set topic")
#         return data
#
#     class Meta:
#         model = Comment
#         fields = (
#             "id",
#             "topic",
#             "text",
#             "comment",
#             "created_at",
#             "updated_at",
#             "user",
#             "comment_comments",
#         )
#         extra_kwargs = {
#             "text": {"required": True},
#             "comment_comments": {"read_only": True},
#         }


class MembershipSerializer(serializers.ModelSerializer):
    inviter = PublicUserSimpleSerializer(read_only=True)
    user = PublicUserSimpleSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(source="user", queryset=User.objects.all(), many=False,
                                                 write_only=True, required=False)
    topic_title = serializers.CharField(source="topic.title", read_only=True)

    class Meta:
        model = Membership
        fields = "__all__"
