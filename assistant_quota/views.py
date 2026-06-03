from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from utils.multilinguality import MultilingualityViewMixin
from .models import get_usage_snapshot, try_consume, RequestPack
from .serializers import RequestPackSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def assistant_usage(request):
    """Returns the current quota usage snapshot for the authenticated user."""
    return Response(get_usage_snapshot(request.user))


@api_view(["GET"])
@permission_classes([AllowAny])
def request_packs_list(request):
    """Returns the list of active request packs ordered by sort_order."""
    language_code = None
    lang = request.query_params.get("language_code") or request.query_params.get("lang")
    if lang:
        language_code = lang.split("-")[0].lower()
    else:
        accept_lang = request.META.get("HTTP_ACCEPT_LANGUAGE", "")
        if accept_lang:
            primary = accept_lang.split(",")[0].split(";")[0].strip()
            if primary:
                language_code = primary.split("-")[0].lower()
        if not language_code and request.user and request.user.is_authenticated:
            language_code = getattr(request.user, "language", None)
            if language_code:
                language_code = language_code.split("-")[0].lower()

    queryset = RequestPack.objects.filter(is_active=True)
    serializer = RequestPackSerializer(
        queryset, many=True, context={"language_code": language_code, "request": request}
    )
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def assistant_consume(request):
    """Atomically debits one request from the user's quota.

    Responds with 200 + snapshot on success, 403 if the user's tariff has no
    assistant access at all, 429 if any active limit is exhausted.
    """
    result = try_consume(request.user)
    if result["ok"]:
        return Response(result["snapshot"], status=status.HTTP_200_OK)

    if result["reason"] == "no_access":
        return Response(
            {"detail": "Assistant access is not included in your tariff.", **result},
            status=status.HTTP_403_FORBIDDEN,
        )
    return Response(
        {"detail": "Quota exceeded.", **result}, status=status.HTTP_429_TOO_MANY_REQUESTS,
    )
