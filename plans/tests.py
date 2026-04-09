from unittest.mock import MagicMock, patch

import pytest
import requests
from rest_framework.test import APIClient

from profiles.models import UserProfile
from plans.clients.recipes import RecipesServiceClient
from plans.models import MealPlan
from plans.similarity import calculate_similarity


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture(autouse=True)
def _disable_mock_recipes_by_default(settings):
    """Тесты явно мокают HTTP; MOCK_RECIPES из окружения не должен ломать их."""
    settings.MOCK_RECIPES = False


def _three_recipes_2000_kcal():
    return [
        {
            'id': 1,
            'name': 'Завтрак А',
            'tags': [{'id': 1, 'name': 'завтрак'}],
            'ingredients': [{'id': 101, 'name': 'овсянка'}],
            'calories': 650,
        },
        {
            'id': 2,
            'name': 'Обед Б',
            'tags': [{'id': 2, 'name': 'обед'}],
            'ingredients': [{'id': 102, 'name': 'курица'}],
            'calories': 650,
        },
        {
            'id': 3,
            'name': 'Ужин В',
            'tags': [{'id': 3, 'name': 'ужин'}],
            'ingredients': [{'id': 103, 'name': 'рыба'}],
            'calories': 700,
        },
    ]


def test_calculate_similarity_identical():
    r = {
        'tags': [{'id': 1}],
        'ingredients': [{'id': 10, 'name': 'рис'}],
    }
    assert calculate_similarity(r, r) == pytest.approx(1.0)


def test_calculate_similarity_no_overlap():
    a = {'tags': [{'id': 1}], 'ingredients': [{'id': 10}]}
    b = {'tags': [{'id': 2}], 'ingredients': [{'id': 20}]}
    assert calculate_similarity(a, b) == pytest.approx(0.0)


def test_calculate_similarity_partial():
    a = {'tags': [{'id': 1}, {'id': 2}], 'ingredients': [{'id': 10}]}
    b = {'tags': [{'id': 2}, {'id': 3}], 'ingredients': [{'id': 11}]}
    # один общий тег id=2 из пяти элементов в объединении
    assert calculate_similarity(a, b) == pytest.approx(0.2)


@pytest.mark.django_db
def test_generate_plan_success(api_client, settings):
    settings.RECIPES_SERVICE_URL = 'http://recipes.test'
    settings.AUTH_SERVICE_URL = ''

    UserProfile.objects.create(user_id=5, daily_calories=2000, excluded_ingredients='')

    with patch.object(RecipesServiceClient, 'list_recipes', return_value=_three_recipes_2000_kcal()):
        response = api_client.post('/plans/generate/', HTTP_X_USER_ID='5')

    assert response.status_code == 201
    assert response.data['user_id'] == 5
    assert len(response.data['payload']['days']) == 7
    for day in response.data['payload']['days']:
        assert day['total_calories'] == 2000
    assert MealPlan.objects.filter(user_id=5).count() == 1


@pytest.mark.django_db
def test_generate_requires_profile(api_client, settings):
    settings.RECIPES_SERVICE_URL = 'http://recipes.test'
    settings.AUTH_SERVICE_URL = ''

    with patch.object(RecipesServiceClient, 'list_recipes', return_value=_three_recipes_2000_kcal()):
        response = api_client.post('/plans/generate/', HTTP_X_USER_ID='99')

    assert response.status_code == 404


@pytest.mark.django_db
def test_generate_recipes_service_not_configured(api_client, settings):
    settings.RECIPES_SERVICE_URL = ''
    settings.MOCK_RECIPES = False
    UserProfile.objects.create(user_id=1, daily_calories=2000)

    response = api_client.post('/plans/generate/', HTTP_X_USER_ID='1')

    assert response.status_code == 503


@pytest.mark.django_db
def test_generate_with_mock_recipes_no_external_url(api_client, settings):
    settings.MOCK_RECIPES = True
    settings.RECIPES_SERVICE_URL = ''
    settings.AUTH_SERVICE_URL = ''
    UserProfile.objects.create(user_id=50, daily_calories=2000, excluded_ingredients='')

    response = api_client.post('/plans/generate/', HTTP_X_USER_ID='50')

    assert response.status_code == 201
    assert len(response.data['payload']['days']) == 7


@pytest.mark.django_db
def test_generate_auth_user_not_found(api_client, settings):
    settings.RECIPES_SERVICE_URL = 'http://recipes.test'
    settings.AUTH_SERVICE_URL = 'http://auth.test'
    UserProfile.objects.create(user_id=2, daily_calories=2000)

    with patch.object(RecipesServiceClient, 'list_recipes', return_value=_three_recipes_2000_kcal()):
        with patch('plans.views.AuthServiceClient.user_exists', return_value=False):
            response = api_client.post('/plans/generate/', HTTP_X_USER_ID='2')

    assert response.status_code == 404
    assert 'auth' in response.data['error'].lower() or 'пользователь' in response.data['error'].lower()


@pytest.mark.django_db
def test_generate_recipes_service_error(api_client, settings):
    settings.RECIPES_SERVICE_URL = 'http://recipes.test'
    settings.AUTH_SERVICE_URL = ''
    UserProfile.objects.create(user_id=3, daily_calories=2000)

    with patch.object(
        RecipesServiceClient,
        'list_recipes',
        side_effect=requests.ConnectionError('boom'),
    ):
        response = api_client.post('/plans/generate/', HTTP_X_USER_ID='3')

    assert response.status_code == 502


@pytest.mark.django_db
def test_generate_excludes_all_recipes_returns_400(api_client, settings):
    settings.RECIPES_SERVICE_URL = 'http://recipes.test'
    settings.AUTH_SERVICE_URL = ''
    UserProfile.objects.create(
        user_id=4,
        daily_calories=2000,
        excluded_ingredients='курица, рыба, овсянка',
    )

    recipes = _three_recipes_2000_kcal()

    with patch.object(RecipesServiceClient, 'list_recipes', return_value=recipes):
        response = api_client.post('/plans/generate/', HTTP_X_USER_ID='4')

    assert response.status_code == 400
    assert 'исключ' in response.data['error'].lower() or 'рецепт' in response.data['error'].lower()


@pytest.mark.django_db
def test_generate_respects_exclusions_uses_only_allowed_recipe(api_client, settings):
    settings.RECIPES_SERVICE_URL = 'http://recipes.test'
    settings.AUTH_SERVICE_URL = ''
    UserProfile.objects.create(user_id=41, daily_calories=2000, excluded_ingredients='курица, рыба')

    with patch.object(RecipesServiceClient, 'list_recipes', return_value=_three_recipes_2000_kcal()):
        response = api_client.post('/plans/generate/', HTTP_X_USER_ID='41')

    assert response.status_code == 201
    for day in response.data['payload']['days']:
        for meal in day['meals']:
            assert meal['recipe_id'] == 1


@pytest.mark.django_db
def test_get_plan_detail(api_client, settings):
    settings.RECIPES_SERVICE_URL = 'http://recipes.test'
    settings.AUTH_SERVICE_URL = ''
    UserProfile.objects.create(user_id=6, daily_calories=2000)

    with patch.object(RecipesServiceClient, 'list_recipes', return_value=_three_recipes_2000_kcal()):
        create = api_client.post('/plans/generate/', HTTP_X_USER_ID='6')
    plan_id = create.data['id']

    response = api_client.get(f'/plans/{plan_id}/', HTTP_X_USER_ID='6')

    assert response.status_code == 200
    assert response.data['id'] == plan_id


@pytest.mark.django_db
def test_get_plan_forbidden_other_user(api_client, settings):
    settings.RECIPES_SERVICE_URL = 'http://recipes.test'
    settings.AUTH_SERVICE_URL = ''
    UserProfile.objects.create(user_id=7, daily_calories=2000)
    UserProfile.objects.create(user_id=8, daily_calories=2000)

    with patch.object(RecipesServiceClient, 'list_recipes', return_value=_three_recipes_2000_kcal()):
        create = api_client.post('/plans/generate/', HTTP_X_USER_ID='7')
    plan_id = create.data['id']

    response = api_client.get(f'/plans/{plan_id}/', HTTP_X_USER_ID='8')

    assert response.status_code == 403


def test_recipes_client_follows_pagination():
    session = MagicMock()
    first = MagicMock()
    first.json.return_value = {
        'results': [{'id': 1, 'name': 'a'}],
        'next': 'http://recipes/recipes/?page=2',
    }
    second = MagicMock()
    second.json.return_value = {
        'results': [{'id': 2, 'name': 'b'}],
        'next': None,
    }
    session.get.side_effect = [first, second]
    client = RecipesServiceClient('http://recipes', session=session)
    out = client.list_recipes()
    assert len(out) == 2
    assert session.get.call_count == 2
