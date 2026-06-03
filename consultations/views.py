from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny

from .models import Consultation
from .serializers import ConsultationSerializer


class ConsultationCreateView(CreateAPIView):
    queryset = Consultation.objects.all()
    serializer_class = ConsultationSerializer
    permission_classes = (AllowAny,)

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(user=user)
