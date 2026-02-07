from django.forms import model_to_dict
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from info.models import Info, Documents, MobileAppsVersion, AppPartInfo
from info.serializers import AppPartInfoSerializer, DocumentsSerializer

from utils.multilinguality import get_default_language_code


@api_view(['GET'])
def get_info(request):
    info = Info.objects.last()
    if info:
        return Response(model_to_dict(info))
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
def get_document(request, code):
    info = Documents.objects.filter(code=code, published_at__isnull=False).last()
    if info:
        return Response(
            DocumentsSerializer(
                info,
                context={"language_code": request.GET.get("language_code", get_default_language_code())}
            ).data
        )
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
def get_app_part_info(request, code):
    info = AppPartInfo.objects.filter(code=code).last()
    if info:
        return Response(
            AppPartInfoSerializer(
                info,
                context={"language_code": request.GET.get("language_code", get_default_language_code())}
            ).data
        )
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
def get_mobile_app_version(request, app_type):
    info = MobileAppsVersion.objects.filter(app_type=app_type).last()
    if info:
        return Response(model_to_dict(info))
    return Response(status=status.HTTP_204_NO_CONTENT)
