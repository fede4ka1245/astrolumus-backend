import pytest
from pytest_drf import (
    Returns200,
    UsesPostMethod,
)
from pytest_lambda import lambda_fixture, static_fixture
from utils.pytest_drf import APIViewTest, url_for


class TestTokenObtainPair(APIViewTest, UsesPostMethod, Returns200):
    @pytest.fixture
    def common_subject(self, db, authenticated_client, django_user_model, get_response):
        user = django_user_model.objects.get(first_name='user')
        user.set_password('53cr3tP455w0rD')
        user.save()
        yield get_response
        user.password = '!invalid'
        user.save()
    url = lambda_fixture(lambda: url_for('token_obtain_pair'))
    data = static_fixture({
        'email': 'test3@test.com',
        'password': '53cr3tP455w0rD',
    })


class TestTokenRefresh(APIViewTest, UsesPostMethod, Returns200):
    @pytest.fixture
    def common_subject(self, db, get_response):
        return get_response

    @pytest.fixture
    def refresh_token(self, client, django_user_model):
        user = django_user_model.objects.get(first_name='user')
        user.set_password('53cr3tP455w0rD')
        user.save()
        result = client.post(
            url_for('token_obtain_pair'),
            data={
                'email': 'test3@test.com',
                'password': '53cr3tP455w0rD',
            },
        )
        yield result.json()['refresh']
        user.password = '!invalid'
        user.save()

    url = lambda_fixture(lambda: url_for('token_refresh'))

    @pytest.fixture
    def data(self, refresh_token):
        return {'refresh': refresh_token}


class TestTokenVerify(APIViewTest, UsesPostMethod, Returns200):
    @pytest.fixture
    def common_subject(self, db, get_response):
        return get_response

    @pytest.fixture
    def access_token(self, client, django_user_model):
        user = django_user_model.objects.get(first_name='user')
        user.set_password('53cr3tP455w0rD')
        user.save()
        result = client.post(
            url_for('token_obtain_pair'),
            data={
                'email': 'test3@test.com',
                'password': '53cr3tP455w0rD',
            },
        )
        yield result.json()['access']
        user.password = '!invalid'
        user.save()

    url = lambda_fixture(lambda: url_for('jwt:token-verify'))

    @pytest.fixture
    def data(self, access_token):
        return {'token': access_token}
