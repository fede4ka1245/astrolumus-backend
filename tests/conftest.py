from pathlib import Path
import pytest

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command


def pytest_sessionfinish(session, exitstatus):
    """ Allows empty test suite. """
    if exitstatus == pytest.ExitCode.NO_TESTS_COLLECTED:
        session.exitstatus = pytest.ExitCode.OK


@pytest.fixture(scope='module')
def wojak(request):
    """ A file fixture to test file upload. """
    with open(Path(request.fspath).parent / 'files' / 'wojak.jpg', 'rb') as p:
        return SimpleUploadedFile('wojak.jpg', p.read(), content_type='image/jpeg')


@pytest.fixture(scope='module')
def pepe(request):
    """ Another file fixture. """
    with open(Path(request.fspath).parent / 'files' / 'pepe.jpg', 'rb') as p:
        return SimpleUploadedFile('pepe.jpg', p.read(), content_type='image/jpeg')


@pytest.fixture(scope='module', autouse=True)
def django_db_setup(request, django_db_setup, django_db_blocker):
    """
    Makes logged-in users with various access rights available in all tests.
    Just use the right user as a parameter of the `common_subject()` method.
    """
    with django_db_blocker.unblock():
        # make user objects available
        call_command(
            'loaddata',
            Path(request.fspath).parent / 'fixtures' / 'users.json',
        )
        yield
        # cleanup
        call_command('flush', '--no-input')


@pytest.fixture
def admin_client(client, django_user_model):
    """ Admin user. """
    admin = django_user_model.objects.get(first_name='admin')
    client.force_login(admin)
    return client


@pytest.fixture
def staff_client(client, django_user_model):
    """ Staff user. """
    admin = django_user_model.objects.get(first_name='staff')
    client.force_login(admin)
    return client


@pytest.fixture
def authenticated_client(client, django_user_model):
    """ Ordinary user. """
    user = django_user_model.objects.get(first_name='user')
    client.force_login(user)
    return client
