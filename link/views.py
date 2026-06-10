from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from .serializers import LinkSerializer
from .models import Link


class LinkView(GenericAPIView):
    permission_classes = ()

    def get(self, request, id):
        # Unknown uuid -> 404 (not 500). The route is <str:id>, so a malformed
        # uuid would raise ValidationError from the UUIDField lookup; map that
        # to 404 as well.
        try:
            link = get_object_or_404(Link, link_uid=id)
        except (ValidationError, ValueError):
            raise Http404("Link not found.")

        # TODO(open-redirect): Link.link is an arbitrary client-supplied URL
        # (CreateLinkView is unauthenticated) and neither the model nor the
        # creation code records an allowed origin to validate against, so the
        # redirect target cannot be constrained here without a product decision
        # on permitted hosts. Revisit: validate/allowlist at creation time.
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
