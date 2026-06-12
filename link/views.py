from datetime import timedelta
from urllib.parse import urlencode

from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import redirect
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from .serializers import LinkSerializer
from .models import Link


def _fallback_target_from_horoscope(build_uid):
    """Reconstruct the canonical /app URL for a build whose Link row is
    missing (the client-side registerBuildLink is fire-and-forget and dies if
    the tab closes mid-flight). MyHoroscope + HoroscopeCache carry everything
    the SPA needs; the format mirrors buildHoroscopeUrl on the frontend:

        /app?city=…&hours=3&minutes=00&greenwich=+&latitude=…&longitude=…
            &name=…&date=DD.MM.YYYY&time=HH:MM:SS&build=<uid>

    Returns a RELATIVE url (same-origin redirect works on both domains), or
    None when no saved horoscope carries this build uid.
    """
    from horoscope.models import MyHoroscope

    saved = (
        MyHoroscope.objects.filter(build_uid=str(build_uid))
        .select_related("horoscope")
        .first()
    )
    if saved is None:
        return None

    cache = saved.horoscope
    try:
        tz_hours = int(cache.tz_hour)
        tz_minutes = int(cache.tz_minutes or 0)
    except (TypeError, ValueError):
        tz_hours, tz_minutes = 0, 0
    sign = -1 if tz_hours < 0 else 1
    # cache.dt is the birth moment in UTC; the SPA expects the LOCAL wall time.
    local_dt = cache.dt + sign * timedelta(hours=abs(tz_hours), minutes=tz_minutes)

    params = {
        "city": saved.city,
        "hours": str(abs(tz_hours)),
        "minutes": f"{tz_minutes:02d}",
        "greenwich": "-" if sign < 0 else "+",
        "latitude": cache.latitude,
        "longitude": cache.longitude,
        "name": saved.name,
        "date": local_dt.strftime("%d.%m.%Y"),
        "time": local_dt.strftime("%H:%M:%S"),
        "build": str(build_uid),
    }
    return f"/app?{urlencode(params)}"


class LinkView(GenericAPIView):
    # No SessionAuthentication: the view is public, and a stray admin session
    # cookie must not drag CSRF checks into it.
    authentication_classes = ()
    permission_classes = ()

    def get(self, request, id):
        # Unknown uuid -> 404 (not 500). The route is <str:id>, so a malformed
        # uuid would raise ValidationError from the UUIDField lookup; map that
        # to 404 as well.
        try:
            link = Link.objects.filter(link_uid=id).first()
        except (ValidationError, ValueError):
            raise Http404("Link not found.")

        if link is None:
            # The Link row may be missing while the build itself exists (the
            # client-side registration is best-effort) — serve the share/open
            # anyway by rebuilding the canonical URL from the saved horoscope.
            target = _fallback_target_from_horoscope(id)
            if target is None:
                raise Http404("Link not found.")
            return redirect(target)

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
    # No SessionAuthentication — see LinkView. Without this, a browser that is
    # logged into /admin sends its session cookie and DRF enforces CSRF on the
    # POST, silently breaking the fire-and-forget registerBuildLink call.
    authentication_classes = ()
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
