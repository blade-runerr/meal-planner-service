import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from profiles.models import UserProfile


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_create_profile_success(api_client):
    """POST /profiles creates a new profile and returns 201."""
    response = api_client.post(
        '/profiles/',
        data={'daily_calories': 2500},
        format='json',
        HTTP_X_USER_ID='42',
    )
    assert response.status_code == 201
    assert response.data['user_id'] == 42
    assert response.data['daily_calories'] == 2500
    assert UserProfile.objects.filter(user_id=42).exists()


@pytest.mark.django_db
def test_create_profile_missing_header(api_client):
    """POST /profiles without X-User-Id header returns 400."""
    response = api_client.post(
        '/profiles/',
        data={'daily_calories': 2000},
        format='json',
    )
    assert response.status_code == 400
    assert 'error' in response.data


@pytest.mark.django_db
def test_get_profile_me_success(api_client):
    """GET /profiles/me returns existing profile for the user."""
    UserProfile.objects.create(user_id=7, daily_calories=1800)

    response = api_client.get('/profiles/me/', HTTP_X_USER_ID='7')

    assert response.status_code == 200
    assert response.data['user_id'] == 7
    assert response.data['daily_calories'] == 1800


@pytest.mark.django_db
def test_get_profile_me_not_found(api_client):
    """GET /profiles/me returns 404 when profile does not exist."""
    response = api_client.get('/profiles/me/', HTTP_X_USER_ID='999')

    assert response.status_code == 404
    assert 'error' in response.data
