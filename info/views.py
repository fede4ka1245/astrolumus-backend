from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from info.models import Info, Documents, MobileAppsVersion, AppPartInfo
from info.serializers import AppPartInfoSerializer, DocumentsSerializer, InfoSerializer, MobileAppsVersionSerializer

from utils.multilinguality import get_default_language_code


def _resolve_language_code(request):
    lang = request.GET.get("language_code") or request.GET.get("lang")
    if lang:
        return lang.split('-')[0].lower()
    accept_lang = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
    if accept_lang:
        primary = accept_lang.split(',')[0].split(';')[0].strip().split('-')[0].lower()
        if primary:
            return primary
    user = request.user
    if user and user.is_authenticated and getattr(user, 'language', None):
        return user.language.split('-')[0].lower()
    return get_default_language_code()


@api_view(['GET'])
def get_info(request):
    info = Info.objects.last()
    if info:
        return Response(
            InfoSerializer(info, context={"language_code": _resolve_language_code(request)}).data
        )
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
def get_document(request, code):
    info = Documents.objects.filter(code=code, published_at__isnull=False).last()
    if info:
        return Response(
            DocumentsSerializer(
                info,
                context={"language_code": _resolve_language_code(request)}
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
                context={"language_code": _resolve_language_code(request)}
            ).data
        )
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
def get_mobile_app_version(request, app_type):
    info = MobileAppsVersion.objects.filter(app_type=app_type).last()
    if info:
        return Response(
            MobileAppsVersionSerializer(info, context={"language_code": _resolve_language_code(request)}).data
        )
    return Response(status=status.HTTP_204_NO_CONTENT)
