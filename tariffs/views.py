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
            # create default tariff
            Tariff.objects.get_user_tariffs(user=user)

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
    serializer = TariffSerializer(tariff, context={"request": request})

    return Response(status=status.HTTP_200_OK, data=serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user_tariffs(request):
    tariffs = Tariff.objects.get_user_tariffs(user=request.user)
    serializer = TariffSerializer(tariffs, many=True, context={"request": request})

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
        # Return localized data for specific language
        language_code = lang if lang in ['ru', 'en', 'uk', 'pl'] else get_default_language_code()
        serializer = PublicTariffSerializer(
            tariffs,
            many=True,
            context={
                "language_code": language_code,
            }
        )

    return Response(status=status.HTTP_200_OK, data=serializer.data)
