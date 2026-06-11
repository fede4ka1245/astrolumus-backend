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
        #
        # The build uid rides along into the SPA URL so the assistant chat can
        # bind to THIS exact build (per-horoscope chat buckets).
        target = link.link
        if 'build=' not in target:
            target = f"{target}{'&' if '?' in target else '?'}build={link.link_uid}"
        return redirect(target)


class CreateLinkView(GenericAPIView):
    permission_classes = ()
    serializer_class = LinkSerializer

    def post(self, request):
        serialized_data = self.serializer_class(data=request.data)
        serialized_data.is_valid(raise_exception=True)

        target = serialized_data.validated_data.get('link')

        # The client may supply its own uid (the build uid minted at chart
        # build time) so that /horoscope/<build_uid> resolves directly. The
        # value must be a valid UUID; anything else falls back to server-side
        # generation. Re-registering an existing uid is a no-op (idempotent).
        requested_uid = request.data.get('uid')
        if requested_uid:
            try:
                import uuid as _uuid
                parsed_uid = _uuid.UUID(str(requested_uid))
            except (ValueError, AttributeError, TypeError):
                parsed_uid = None
            if parsed_uid is not None:
                link = Link.objects.filter(link_uid=parsed_uid).first()
                if link is None:
                    link = Link.objects.create(link_uid=parsed_uid, link=target)
                return Response(data={"short_link": f'{request.build_absolute_uri()}{link.link_uid}'})

        # Dedupe: the same canonical URL always maps to the same uid. filter()
        # instead of get_or_create — historical duplicates may already exist.
        link = Link.objects.filter(link=target).first()
        if link is None:
            link = Link.objects.create(link=target)

        return Response(data={"short_link": f'{request.build_absolute_uri()}{link.link_uid}'})
