from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction, IntegrityError
from django.db.models import Q, OuterRef, Subquery, Func, F
from django.http import JsonResponse
from django.utils import timezone
from django.utils.timezone import now

from django_filters.rest_framework import DjangoFilterBackend

from notifications.signals import notify

from rest_framework import mixins, status, views, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from voting.models import Vote

from complaints.models import Complaint
from tariffs.models import Tariff

from .filters import UserFilter, SubscriptionFilter

from .models import (
    BlockedUser,
    GeneratedPassword,
    Subscription,
    UserFile,
    UserProfile,
    AppLanguage
)
from .serializers import (
    BlockedUserSerializer,
    GenerateRegistrationCodeSerializer,
    RegistrationSerializer,
    SubscriptionSerializer,
    UserFileSerializer,
    UserProfileOpenInfoSerializer,
    UserProfileSerializer,
    UserSerializer,
    ValidateRegistrationCodeSerializer,
    PublicUserSerializer,
    AppLanguageSerializer
)

from tariffs.serilizers import TariffSerializer

User = get_user_model()

SMS_TIMEOUT = 60
CODE_VALID_MINUTES = 10


class RegistrationAPIViewSet(GenericViewSet, mixins.CreateModelMixin, ):
    permission_classes = (AllowAny,)
    serializer_class = RegistrationSerializer

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        user.set_unusable_password()
        user.save()

        # new user do not have GeneratedPassword yet, so just create
        password = GeneratedPassword.objects.create(user=user)

        try:
            # todo get email from setting
            send_mail(
                'Код доступа AlphaSpace',
                f'Ваш код авторизации: {password.password}',
                'alphaspace@alpha-astro.com',
                [user.email],
                fail_silently=False,
            )
        except Exception as e:
            return Response(
                status=405, data={"message": "Произошла ошибка, попробуйте позже."}
            )

        # set tariff by default
        Tariff.objects.get_user_tariff(user=user)

        # send
        data = {"message": "Код выслан на email"}

        return Response(data, status=status.HTTP_201_CREATED)


class UserCanUpdateItSelf(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in ("DELETE", "PUT", "PATCH"):
            if request.user and (request.user == obj or request.user.is_staff or request.user.is_superuser):
                return True
            else:
                return False
        return True


class UserView(mixins.RetrieveModelMixin,
               mixins.UpdateModelMixin,
               mixins.DestroyModelMixin,
               mixins.ListModelMixin,
               GenericViewSet):
    permission_classes = (IsAuthenticated, UserCanUpdateItSelf)
    serializer_class = PublicUserSerializer
    lookup_field = "id"
    filter_backends = (DjangoFilterBackend,)
    filterset_class = UserFilter
    queryset = User.objects.all()
    ordering = ('-id',)

    def get_serializer_class(self):
        if self.request.user.is_authenticated and (self.request.user.is_staff or self.request.user.is_superuser):
            return UserSerializer
        if self.action == "retrieve" and self.request.user == self.get_object():
            return UserSerializer
        if self.action == "me":
            return UserSerializer
        return self.serializer_class

    @action(methods=['GET'], detail=False)
    def me(self, request):
        serializer = self.get_serializer(self.request.user, many=False)
        return Response(serializer.data)

    @action(methods=['GET'], detail=False)
    def me_with_tariffs(self, request):
        """Get current user with their active tariffs"""
        user = self.request.user
        tariffs = Tariff.objects.get_user_tariffs(user)
        
        user_serializer = self.get_serializer(user, many=False)
        tariffs_serializer = TariffSerializer(tariffs, many=True, context={'request': request})
        
        data = {
            'user': user_serializer.data,
            'tariffs': tariffs_serializer.data
        }
        return Response(data)

    @action(methods=['post'], detail=True, url_path="like", permission_classes=[IsAuthenticated, ])
    def like(self, request, *args, **kwargs):
        user = self.get_object()
        vote = Vote.objects.get_for_user(user, request.user)
        new_vote = 1
        if vote and vote.vote == 1:
            new_vote = 0  # remove vote
        Vote.objects.record_vote(user, request.user, new_vote)
        return JsonResponse(data={"likes_count": Vote.objects.get_score(user)["score"]}, status=status.HTTP_200_OK)

    @action(methods=['post'], detail=True, url_path="complaint", permission_classes=[IsAuthenticated, ])
    def complaint(self, request, *args, **kwargs):
        details = request.data.get("details", "")
        c = Complaint(content_object=self.get_object(), user=request.user, details=details)
        c.save()
        return JsonResponse(data={}, status=status.HTTP_200_OK)


class GenerateLoginCodeAPIView(views.APIView):
    permission_classes = (AllowAny,)
    serializer_class = GenerateRegistrationCodeSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = User.objects.get(email=str(serializer.data["email"]).lower())
        except User.DoesNotExist:
            return Response(
                status=404, data={"message": "Пользователь не найден."}
            )

        expiry_date = timezone.now() - timedelta(minutes=CODE_VALID_MINUTES)

        password = GeneratedPassword.objects.filter(
            user=user
        ).first()
        if password:
            if password.date < expiry_date:
                # renew code
                GeneratedPassword.objects.filter(
                    user=user
                ).delete()  # delete all codes
                password = GeneratedPassword.objects.create(
                    user=user
                )
        else:
            password = GeneratedPassword.objects.create(
                user=user
            )

        try:
            # send email TODO use user lang/templates
            # todo get email from settings
            send_mail(
                'Код доступа AlphaSpace',
                f'Ваш код авторизации: {password.password}',
                'alphaspace@alpha-astro.com',
                [user.email],
                fail_silently=False,
            )
        except Exception as e:
            return Response(
                status=405, data={"message": "Произошла ошибка, попробуйте позже."}
            )

        # send
        data = {"message": "Код выслан на email"}

        # set tariff by default
        Tariff.objects.get_user_tariff(user=user)

        return Response(data, status=status.HTTP_200_OK)


class ValidateLoginCodeAPIView(views.APIView):
    permission_classes = (AllowAny,)
    serializer_class = ValidateRegistrationCodeSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        submitted_password = serializer.data["password"]

        user = User.objects.filter(email=serializer.data["email"].lower()).first()
        expiry_date = timezone.now() - timedelta(minutes=CODE_VALID_MINUTES)

        password = GeneratedPassword.objects.filter(
            user=user, attempts__lt=2, date__gte=expiry_date
        )

        if not password:
            return Response(
                status=405, data={"message": "Необходимо сгенерировать новый пароль."}
            )

        if submitted_password != password.first().password:
            return Response(status=405, data={"message": "Неверный пароль."})
        else:
            password.delete()  # delete all tokens
            data = user.generate_tokens()

            user.last_login = now()
            user.save()

            return Response(data, status=status.HTTP_200_OK)


class UserFileViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserFileSerializer
    lookup_field = "id"
    queryset = UserFile.objects.all()
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ["user", "file_type"]

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UserProfileView(
    mixins.UpdateModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserProfileSerializer
    queryset = UserProfile.objects.all()

    def get_object(self):
        user = self.request.user
        try:
            # Ensure atomic operation for retrieval or creation
            with transaction.atomic():
                user_profile, created = UserProfile.objects.get_or_create(user=user)
                return user_profile
        except User.DoesNotExist:
            raise NotFound()
        except IntegrityError:
            return self.queryset.get(user=user)

    def create(self, request, *args, **kwargs):
        user_profile = UserProfile.objects.filter(user=self.request.user).first()

        if user_profile:
            return super().update(request, *args, **kwargs)
        else:
            return super().create(request, *args, **kwargs)

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SubscriptionViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = Subscription.objects.all().select_related("user_dst", "user_src")
    serializer_class = SubscriptionSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = SubscriptionFilter

    # filterset_fields = ["status", "user_dst", "user_src"]

    def get_queryset(self):
        # get subscription only for users take a part
        qs = (
            super()
                .get_queryset()
                .filter(Q(user_dst=self.request.user) | Q(user_src=self.request.user) | Q(status=1))
        )
        return qs

    def perform_create(self, serializer):
        instance = serializer.save(user_src=self.request.user)
        notify.send(instance.user_src, recipient=instance.user_dst, action_object=instance.user_dst,
                    verb='subscribed to user')

    @action(methods=['DELETE'], detail=False)
    def delete(self, request):
        try:
            subscription = self.get_queryset().get(user_src=self.request.user,
                                                   user_dst=request.data.get("user_dst_id", None))
            subscription.delete()
        except Subscription.DoesNotExist:
            pass
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['POST'], detail=False)
    def accept(self, request):
        try:
            subscription = self.get_queryset().get(user_dst=self.request.user,
                                                   user_src=request.data.get("user_src_id", None))
            subscription.status = 1
            subscription.save()
        except Subscription.DoesNotExist:
            return Response(data={"error": "Subscription not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(subscription, many=False)
        return Response(serializer.data)

    @action(methods=['POST'], detail=False)
    def reject(self, request):
        try:
            subscription = self.get_queryset().get(user_dst=self.request.user,
                                                   user_src=request.data.get("user_src_id", None))
            subscription.status = 2
            subscription.save()
        except Subscription.DoesNotExist:
            return Response(data={"error": "Subscription not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(subscription, many=False)
        return Response(serializer.data)


class BlockedUserViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = (IsAuthenticated,)
    queryset = BlockedUser.objects
    serializer_class = BlockedUserSerializer

    def get_queryset(self):
        qs = super().get_queryset().filter(user_src=self.request.user)
        return qs

    def perform_create(self, serializer):
        serializer.save(user_src=self.request.user)


class FriendsView(
    mixins.ListModelMixin, viewsets.GenericViewSet
):
    permission_classes = (IsAuthenticated,)
    serializer_class = PublicUserSerializer
    lookup_field = "id"
    queryset = User.objects.all()
    filter_backends = (DjangoFilterBackend,)
    filterset_class = UserFilter

    def get_queryset(self):
        try:
            user_id = self.request.query_params.get("user_src")
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise ValidationError("please specify user_src get parameter")

        subscribers = user.user_src_subscriptions.filter(status=1)

        qs = (
            super()
                .get_queryset()
                .filter(
                id__in=user.user_dst_subscriptions.filter(status=1)
                    .exclude(
                    ~Q(user_src__in=subscribers.values_list("user_dst", flat=True))
                )
                    .values_list("user_src", flat=True)
            )
        )
        return qs


class UserProfileOpenInfoViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserProfileOpenInfoSerializer
    queryset = UserProfile.objects.all()
    lookup_field = "user_id"

    def get_queryset(self):
        qs = super(UserProfileOpenInfoViewSet, self).get_queryset()
        subscribers = Subscription.objects.filter(
            user_dst=OuterRef("user_id"),
            status=1,
        ).order_by().annotate(
            count=Func(F('id'), function='Count')
        ).values('count')
        return qs.annotate(subscribers_count=Subquery(subscribers))

    def get_object(self):
        user_id = self.kwargs["user_id"]
        try:
            # Ensure atomic operation for retrieval or creation
            with transaction.atomic():
                user_profile, created = UserProfile.objects.get_or_create(
                    user_id=user_id,
                    defaults={"user": User.objects.get(pk=user_id)}
                )
                return user_profile
        except User.DoesNotExist:
            raise NotFound()
        except IntegrityError:
            return self.get_queryset().get(user_id=user_id)


class UserRightsAPIView(views.APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        tariffs = Tariff.objects.get_user_tariffs(user=request.user)
        # user restriction cross
        restriction = {}
        for tariff in tariffs:
            for attr in dir(tariff):
                if not attr.startswith("restriction"):
                    continue
                value = getattr(tariff, attr)
                old_value = restriction.get(attr, None)
                if old_value is None:
                    restriction[attr] = value
                    continue
                # update restriction to the max ones
                if isinstance(value, bool):
                    if old_value is True:
                        restriction[attr] = value
                elif isinstance(value, int):
                    if old_value != 0 and old_value < value:
                        restriction[attr] = value
                    if value == 0:
                        restriction[attr] = 0

        # deny forum if it set in user profile
        if request.user.restriction_forum:
            restriction["restriction_forum"] = True

        return Response(data=restriction, status=status.HTTP_200_OK)


class AppLanguagesView(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = AppLanguageSerializer
    queryset = AppLanguage.objects.all()
