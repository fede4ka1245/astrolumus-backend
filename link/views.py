from rest_framework.generics import GenericAPIView
from django.shortcuts import redirect
from rest_framework.response import Response
from .serializers import LinkSerializer
from .models import Link


class LinkView(GenericAPIView):
    permission_classes = ()

    def get(self, request, id):
        link = Link.objects.get(link_uid=id)

        return redirect(link.link)


class CreateLinkView(GenericAPIView):
    permission_classes = ()
    serializer_class = LinkSerializer

    def post(self, request):
        serialized_data = self.serializer_class(data=request.data)
        serialized_data.is_valid(raise_exception=True)

        link = Link(link=serialized_data.validated_data.get('link'))
        link.save()

        return Response(data={"short_link": f'{request.build_absolute_uri()}{link.link_uid}'})
