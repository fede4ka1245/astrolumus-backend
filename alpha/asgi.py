import os

from django.core.asgi import get_asgi_application

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

from utils.channels_no_route_middleware import RouteNotFoundMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alpha.settings')

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

import chat.routing
from utils.channels_jwt_auth_middleware import JWTAuthMiddleware

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,  # TODO no need in production
        "websocket": AllowedHostsOriginValidator(  # limit to ALLOWED_HOSTS
            JWTAuthMiddleware(
                RouteNotFoundMiddleware(
                    URLRouter(chat.routing.websocket_urlpatterns)))
        ),
    }
)
