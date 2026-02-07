from functools import partial

import pytest
from pytest_drf import views as test_views
from rest_framework.settings import api_settings
from rest_framework.reverse import reverse


def url_for(viewname, *args, _urlconf=None, _current_app=None, **kwargs):
    """
    Similar to `pytest_drf.url_for()`, but also applies the default API version
    to the URL being reversed.
    """
    # kwargs.setdefault(api_settings.VERSION_PARAM, api_settings.DEFAULT_VERSION)
    return reverse(
        viewname, urlconf=_urlconf, current_app=_current_app, args=args, kwargs=kwargs
    )


class APIViewTest(test_views.APIViewTest):
    """
    Temporary workaround (possible pytest-django or drf bug). Allows one to
    redefine the request format for APIView. Default is set to 'json', but
    'multipart' may be used as “old default” (by passing `None` to the fixture)
    and is required for file upload actions.
    """

    @pytest.fixture
    def format(self):
        # request format (JSON by default)
        return 'json'

    @pytest.fixture
    def get_response(self, http_method, format, client):
        # set request format
        return partial(getattr(client, http_method), format=format)


class ViewSetTest(APIViewTest):
    """ Taken from 'pytest-drf'. """

    @pytest.fixture
    def list_url(self):
        raise NotImplementedError('Please define a list_url fixture')

    @pytest.fixture
    def detail_url(self):
        raise NotImplementedError('Please define a detail_url fixture')
