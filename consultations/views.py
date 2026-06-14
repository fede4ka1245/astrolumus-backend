from django.utils.html import escape
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny

from alpha.notifications import send_telegram

from .models import Consultation
from .serializers import ConsultationSerializer


class ConsultationCreateView(CreateAPIView):
    queryset = Consultation.objects.all()
    serializer_class = ConsultationSerializer
    permission_classes = (AllowAny,)

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        consultation = serializer.save(user=user)

        lines = [
            "🔮 <b>Новая запись на консультацию</b>",
            f"<b>Имя:</b> {escape(consultation.name)}",
            f"<b>Контакт:</b> {escape(consultation.contact)}",
        ]
        if consultation.topic:
            lines.append(f"<b>Тема:</b> {escape(consultation.topic)}")
        if consultation.preferred_time:
            lines.append(f"<b>Желаемое время:</b> {escape(consultation.preferred_time)}")
        if consultation.message:
            lines.append(f"<b>Пожелания:</b> {escape(consultation.message)}")
        if user is not None:
            lines.append(f"<b>Аккаунт:</b> {escape(user.email)}")
        lines.append(f"<i>{consultation.created_at:%d.%m.%Y %H:%M}</i>")
        send_telegram("\n".join(lines))
