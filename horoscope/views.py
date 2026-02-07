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
    queryset = MyHoroscope.objects.all()
    filter_backends = (DjangoFilterBackend,)
    filterset_class = MyHoroscopeFilter
    serializer_class = MyHoroscopeSerializer

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

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
