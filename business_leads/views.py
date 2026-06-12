from django.conf import settings
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .serializers import BusinessLeadSerializer


class LeadThrottle(AnonRateThrottle):
    rate = "10/hour"


class BusinessLeadView(APIView):
    """Публичная лид-форма B2B-лендинга. Анти-спам: honeypot-поле `website`
    (заполнено ботом → молча принимаем и выбрасываем) + троттлинг по IP."""

    permission_classes = (AllowAny,)
    authentication_classes = ()
    throttle_classes = (LeadThrottle,)

    def post(self, request, *args, **kwargs):
        if request.data.get("website"):
            return Response({"ok": True}, status=status.HTTP_201_CREATED)

        serializer = BusinessLeadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lead = serializer.save()

        recipients = [email for _, email in getattr(settings, "ADMINS", [])]
        if recipients:
            try:
                send_mail(
                    subject=f"B2B-заявка: {lead.name}",
                    message=(
                        f"Имя: {lead.name}\n"
                        f"Контакт: {lead.contact}\n"
                        f"Комментарий: {lead.comment or '—'}\n"
                        f"Источник: {lead.source}\n"
                        f"Создана: {lead.created_at:%d.%m.%Y %H:%M}"
                    ),
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                    recipient_list=recipients,
                    fail_silently=True,
                )
            except Exception:  # уведомление не должно ронять приём заявки
                pass

        return Response({"ok": True}, status=status.HTTP_201_CREATED)
