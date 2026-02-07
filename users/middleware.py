from django.core.exceptions import PermissionDenied
from django.utils import translation
from django.middleware.locale import LocaleMiddleware
from users.models import user_seen


class UserLanguageMiddleware(LocaleMiddleware):
    def process_request(self, request):
        user = request.user
        if user and user.is_authenticated:
            translation.activate(user.language)
        else:
            super().process_request(request)


def last_seen_middleware(get_response):
    # One-time configuration and initialization.

    def middleware(request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        response = get_response(request)

        if request.user.is_authenticated:
            user_seen(request.user)

        # Code to be executed for each request/response after
        # the view is called.

        return response

    return middleware


def restrict_access_middleware(get_response):
    # One-time configuration and initialization.

    def middleware(request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        response = get_response(request)

        if request.user.is_authenticated and request.user.restriction_forum and request.path.startswith("/forum/"):
            raise PermissionDenied("The forum wad disabled for you by admins")

        # Code to be executed for each request/response after
        # the view is called.

        return response

    return middleware