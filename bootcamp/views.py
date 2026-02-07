from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Course, AdvCourseCard
from .serializers import CourseSerializer, AdvCourseCardSerializer


class CourseViewset(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = ()
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ("course_type",)


class CourseAdvViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = ()
    queryset = AdvCourseCard.objects.filter(show_card=True)
    serializer_class = AdvCourseCardSerializer
    filterset_fields = ("banner_type__alias",)

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('language_code', in_=openapi.IN_QUERY, type=openapi.TYPE_STRING),
        ],
    )
    def get_queryset(self):
        language_param = self.request.query_params.get('language_code', None)
        if language_param:
            self.queryset = self.queryset.filter(target_languages__code=language_param)

        return self.queryset


class CourseAdsViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = ()
    queryset = AdvCourseCard.objects.filter(show_card=True)
    serializer_class = AdvCourseCardSerializer
    pagination_class = None
    filterset_fields = ("banner_type__alias",)


class MyCourseViewset(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    permission_classes = (IsAuthenticated,)
    queryset = Course.objects.all()
    serializer_class = CourseSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user.user_curriculums.all()
        return qs.filter(
            id__in=[
                curriculum.course.pk
                for curriculum in self.request.user.user_curriculums.all()
            ]
        )
