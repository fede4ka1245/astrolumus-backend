from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q, F
from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status

from .models import ActivationTariff, Tariff
from .serilizers import SitePaymentsSerializer, TariffSerializer, PublicTariffSerializer, FullTariffSerializer

from utils.multilinguality import get_default_language_code


User = get_user_model()


def _resolve_language_code(request):
    lang = request.GET.get("language_code")
    if lang:
        return lang
    accept_lang = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
    if accept_lang:
        primary = accept_lang.split(',')[0].split(';')[0].strip().split('-')[0].lower()
        if primary:
            return primary
    user = request.user
    if user and user.is_authenticated and getattr(user, 'language', None):
        return user.language.split('-')[0].lower()
    return get_default_language_code()


@api_view(['POST'])
@transaction.atomic
def payment_from_site(request):
    if not isinstance(request.data, dict):
        return Response(status=status.HTTP_400_BAD_REQUEST)

    token = request.data.get("token", None)
    if token != settings.BACKEND_API_TOKEN:
        return Response(status=status.HTTP_403_FORBIDDEN)

    serializer = SitePaymentsSerializer(data=request.data)
    if serializer.is_valid(raise_exception=True):
        instance = serializer.save()
        # try to find user
        user = None
        try:
            user = User.objects.get(email=instance.email)
        except User.DoesNotExist:
            pass

        tariff_paid = None
        try:
            tariff_paid = Tariff.objects.get(code=instance.tariff_code)
        except Tariff.DoesNotExist:
            raise ValidationError("Tariff with this code not found")

        # activate tariff
        if user and tariff_paid:
            # try to find last activate tariff or already activate tariff from group
            last_activations = ActivationTariff.objects.filter(user=user).filter(
                Q(Q(tariff__validity_days__gt=0)
                  & Q(created_at__gt=timezone.now() - timedelta(days=1) *
                                     F("tariff__validity_days"))) |
                Q(tariff__validity_days=0)
            ).order_by("-created_at")

            tariff_group_last_activation = last_activations.filter(
                Q(tariff=tariff_paid) | Q(tariff__tariff_group_id=tariff_paid.tariff_group)).first()
            if tariff_group_last_activation:
                # if we have non ended activation
                tariff_of_last_activation = tariff_group_last_activation.tariff

                at = ActivationTariff.objects.create(
                    tariff=tariff_paid, user=user)
                at.created_at = tariff_group_last_activation.created_at + timedelta(tariff_of_last_activation.validity_days)
                at.save()
            else:
                # activate now if there is no old group tariff
                ActivationTariff.objects.create(tariff=tariff_paid, user=user)

    return Response(status=status.HTTP_201_CREATED)


@api_view(['POST'])
def check_user_exist(request):
    if not isinstance(request.data, dict):
        return Response(status=status.HTTP_400_BAD_REQUEST)

    token = request.data.get("token", None)
    if token != settings.BACKEND_API_TOKEN:
        return Response(status=status.HTTP_403_FORBIDDEN)

    user_email = request.data.get("email", None)
    if not user_email:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    exist = True
    user = None
    active_tariff_codes = []
    
    try:
        user = User.objects.get(email=user_email)
        active_tariffs = Tariff.objects.get_user_tariffs(user=user)
        active_tariff_codes = list(active_tariffs.values_list('code', flat=True))
    except User.DoesNotExist:
        exist = False

    return Response({
        "user_exist": exist,
        "active_tariff_codes": active_tariff_codes
    }, status=status.HTTP_200_OK)


# FIXME DEPRECATED
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user_tariff(request):
    tariff = Tariff.objects.get_user_tariff(user=request.user)
    if tariff is None:
        return Response(status=status.HTTP_200_OK, data=None)
    language_code = _resolve_language_code(request)
    serializer = TariffSerializer(tariff, context={"request": request, "language_code": language_code})

    return Response(status=status.HTTP_200_OK, data=serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user_tariffs(request):
    tariffs = Tariff.objects.get_user_tariffs(user=request.user)

    language_code = _resolve_language_code(request)
    serializer = TariffSerializer(tariffs, many=True, context={"request": request, "language_code": language_code})

    return Response(status=status.HTTP_200_OK, data=serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def public_tariffs(request):
    tariffs = Tariff.objects.filter(public=True)
    
    # Check if lang=all is requested (return full data with all languages)
    lang = request.GET.get("lang", None)
    
    if lang == "all":
        # Return full data with all languages
        serializer = FullTariffSerializer(tariffs, many=True)
    else:
        # Determine language: query param > Accept-Language > user preference > default
        language_code = None
        if lang and lang in ['ru', 'en', 'uk', 'pl']:
            language_code = lang
        if not language_code:
            accept_lang = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
            if accept_lang:
                primary = accept_lang.split(',')[0].split(';')[0].strip().split('-')[0].lower()
                if primary:
                    language_code = primary
        if not language_code:
            user = request.user
            if user and user.is_authenticated and getattr(user, 'language', None):
                language_code = user.language.split('-')[0].lower()
        if not language_code:
            language_code = get_default_language_code()
        serializer = PublicTariffSerializer(
            tariffs,
            many=True,
            context={
                "language_code": language_code,
            }
        )

    return Response(status=status.HTTP_200_OK, data=serializer.data)
