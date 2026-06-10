import logging

from django.db import IntegrityError
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from astrology_forum.permissions import IsAuthorOrIsAdminOrCreateReadOnly
from .filters import MyHoroscopeFilter
from .models import HoroscopeCache, MyHoroscope
from .serializers import (
    MyHoroscopeSerializer,
    HoroscopeCacheSerializer,
    SettingsSerializer, MyHoroscopeListSerializer
)

logger = logging.getLogger(__name__)


class HoroscopePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"


class HoroscopeCacheViewSet(mixins.CreateModelMixin,
                            mixins.RetrieveModelMixin,
                            mixins.UpdateModelMixin,
                            mixins.ListModelMixin,
                            GenericViewSet):
    permission_classes = (IsAuthenticated,)
    pagination_class = HoroscopePagination
    queryset = HoroscopeCache.objects.all()
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ("my_horoscopes__user",)
    serializer_class = HoroscopeCacheSerializer

    @action(methods=['post'], detail=True, url_path="remove-from-my", permission_classes=[IsAuthenticated, ])
    def remove_from_my(self, request, *args, **kwargs):
        horoscope = self.get_object()
        try:
            # MyHoroscope.objects.get(horoscope=horoscope, user=request.user).delete()
            horoscope.delete()  # it will delete MyHoroscope cascade
        except MyHoroscope.DoesNotExist:
            pass
        return Response(data={}, status=status.HTTP_204_NO_CONTENT)


class MyHoroscopeViewSet(mixins.CreateModelMixin,
                         mixins.ListModelMixin,
                         mixins.UpdateModelMixin,
                         mixins.DestroyModelMixin,
                         GenericViewSet):
    permission_classes = (IsAuthenticated, IsAuthorOrIsAdminOrCreateReadOnly)
    pagination_class = HoroscopePagination
    queryset = MyHoroscope.objects.all().order_by("-created_at")
    filter_backends = (DjangoFilterBackend,)
    filterset_class = MyHoroscopeFilter
    serializer_class = MyHoroscopeSerializer

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        instance = serializer.save()
        # Backfill the user's profile birth_date from this horoscope if not yet set.
        # Only fills empty fields — never overwrites user-set values.
        try:
            from users.models import UserProfile
            profile, _ = UserProfile.objects.get_or_create(user=instance.user)
            horoscope = instance.horoscope
            if not profile.birth_date and horoscope.dt:
                # horoscope.dt encodes the birth WALL-CLOCK time, not a real
                # UTC instant: the client posts a naive "YYYY-MM-DD HH:mm:ss"
                # local birth string which DRF interprets in the server's
                # current timezone (settings.TIME_ZONE) before storing as UTC,
                # and serializes back in that same timezone (the frontend then
                # slices the ISO string and shows it as the birth time,
                # ignoring tz_hour/tz_minutes). localtime() inverts that
                # round-trip exactly, recovering the local birth date for any
                # birth timezone; dt.date() (the UTC date) would shift births
                # near midnight onto the wrong day, and applying
                # tz_hour/tz_minutes would be wrong because dt was never
                # normalized with them in the first place.
                profile.birth_date = timezone.localtime(horoscope.dt).date()
                profile.save(update_fields=["birth_date"])
        except Exception:
            # Backfill is best-effort; never block the horoscope save.
            logger.warning(
                "my-horoscope create: birth_date backfill failed for user %s",
                getattr(instance, "user_id", None),
                exc_info=True,
            )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Auto-save is idempotent: building the same chart again must not 400 on
        # the unique_together [horoscope, user] constraint. Return the existing
        # entry with 200 instead of failing.
        horoscope = serializer.validated_data.get("horoscope")
        existing = MyHoroscope.objects.filter(
            horoscope=horoscope, user=request.user
        ).first()
        if existing is not None:
            return Response(
                self.get_serializer(existing).data, status=status.HTTP_200_OK
            )

        try:
            self.perform_create(serializer)
        except IntegrityError:
            # Concurrent auto-save raced us to the unique_together row; return it.
            existing = MyHoroscope.objects.filter(
                horoscope=horoscope, user=request.user
            ).first()
            return Response(
                self.get_serializer(existing).data, status=status.HTTP_200_OK
            )
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def get_serializer_class(self):
        if self.action == "list":
            return MyHoroscopeListSerializer
        return self.serializer_class

    def perform_destroy(self, instance):
        instance.horoscope.delete()  # it will delete my horoscope with cascade
        # instance.delete()


class SettingsView(GenericAPIView):
    serializer_class = SettingsSerializer
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        serialized_data = self.serializer_class(data=request.data)
        serialized_data.is_valid(raise_exception=True)

        language = serialized_data.validated_data.get("language")
        arudha = serialized_data.validated_data.get("arudha")

        # Users may not have a Settings row yet (settings is a nullable
        # OneToOneField); create one on first save instead of 500-ing.
        if request.user.settings is None:
            from users.models import Settings

            request.user.settings = Settings.objects.create()
            request.user.save(update_fields=["settings"])

        if language is not None:
            request.user.settings.language = language

        if arudha is not None:
            request.user.settings.arudha_scheme = arudha

        request.user.settings.save()

        response = {
            "language": request.user.settings.language,
            "arudha": request.user.settings.arudha_scheme
        }

        return Response(response, status=status.HTTP_201_CREATED)

    def get(self, request, *args, **kwargs):
        if hasattr(request.user, "settings") and request.user.settings:
            response = {
                "language": request.user.settings.language,
                "arudha": request.user.settings.arudha_scheme
            }
        else:
            # TODO
            response = {
                "language": "ru",
                "arudha": 1
            }

        return Response(response, status=status.HTTP_201_CREATED)
