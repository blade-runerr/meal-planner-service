from unittest.mock import MagicMock, patch

import pytest
import requests
from django.core.cache import cache
from rest_framework.test import APIClient

from profiles.models import UserProfile
from plans.clients.mistral import MistralAPIError, MistralClient
from plans.clients.recipes import RecipesServiceClient
from plans.diversity import diversity_score
from plans.models import MealPlan
from plans.services.suggestions_cache import suggestions_cache_key
from plans.services.plan_generator import build_week_payload
from plans.similarity import calculate_similarity


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture(autouse=True)
def _disable_mock_recipes_by_default(settings):
    """Тесты явно мокают HTTP; MOCK_RECIPES из окружения не должен ломать их."""
    settings.MOCK_RECIPES = False


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


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


def test_build_week_tricky_daily_calories_greedy_would_fail_brute_force_ok():
    """Цель 1800 ккал: жадный набор часто даёт тупик; перебор находит допустимую тройку 650+650+700."""
    recipes = _three_recipes_2000_kcal()
    payload = build_week_payload(recipes, 1800, '')
    assert len(payload['days']) == 7
    for day in payload['days']:
        assert day_calories_in_range(day['total_calories'], 1800)


def day_calories_in_range(total: int, target: int) -> bool:
    lo = int(target * 0.68)
    hi = int(target * 1.32) + 1
    return lo <= total <= hi


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
    assert 'diversity_score' in response.data
    assert response.data['diversity_score'] >= 0.0


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


def test_diversity_score_empty_payload():
    assert diversity_score({}) == 0.0


def test_diversity_score_single_meal():
    p = {'days': [{'day_index': 1, 'meals': [{'recipe_id': 5}]}]}
    assert diversity_score(p) == 1.0


def test_diversity_score_all_identical_meals():
    meals = [{'recipe_id': 1} for _ in range(6)]
    p = {'days': [{'day_index': 1, 'meals': meals}]}
    assert diversity_score(p) == pytest.approx(0.5 / 6, abs=1e-3)


def test_diversity_score_alternating():
    meals = [{'recipe_id': i % 2} for i in range(4)]
    p = {'days': [{'day_index': 1, 'meals': meals}]}
    assert diversity_score(p) == pytest.approx(0.5 * (2 / 4) + 0.5 * (3 / 3))


def test_mistral_client_requires_key():
    with pytest.raises(ValueError, match='key'):
        MistralClient('')


def test_mistral_parse_json_suggestions_valid():
    raw = '{"summary": "x", "tips": ["a"]}'
    out = MistralClient.parse_json_suggestions(raw)
    assert out['summary'] == 'x'
    assert out['tips'] == ['a']


def test_mistral_parse_json_suggestions_wrapped_text():
    raw = 'Ответ:\n{"summary": "y", "tips": []}\nспасибо'
    out = MistralClient.parse_json_suggestions(raw)
    assert out['summary'] == 'y'


@pytest.mark.django_db
def test_suggestions_cache_hit_returns_immediately(api_client, settings):
    settings.RECIPES_SERVICE_URL = 'http://recipes.test'
    settings.AUTH_SERVICE_URL = ''
    UserProfile.objects.create(user_id=60, daily_calories=2000)

    with patch.object(RecipesServiceClient, 'list_recipes', return_value=_three_recipes_2000_kcal()):
        create = api_client.post('/plans/generate/', HTTP_X_USER_ID='60')
    plan_id = create.data['id']

    payload = {
        'suggestions': {'summary': 'cached', 'tips': []},
        'diversity_score': 0.9,
        'model': 'mistral-small-latest',
    }
    cache.set(suggestions_cache_key(60, plan_id), payload, timeout=3600)

    response = api_client.get(f'/plans/{plan_id}/suggestions/', HTTP_X_USER_ID='60')
    assert response.status_code == 200
    assert response.data['suggestions']['summary'] == 'cached'


@pytest.mark.django_db
def test_suggestions_forbidden_other_user(api_client, settings):
    settings.RECIPES_SERVICE_URL = 'http://recipes.test'
    settings.AUTH_SERVICE_URL = ''
    UserProfile.objects.create(user_id=61, daily_calories=2000)
    UserProfile.objects.create(user_id=62, daily_calories=2000)

    with patch.object(RecipesServiceClient, 'list_recipes', return_value=_three_recipes_2000_kcal()):
        create = api_client.post('/plans/generate/', HTTP_X_USER_ID='61')
    plan_id = create.data['id']

    response = api_client.get(f'/plans/{plan_id}/suggestions/', HTTP_X_USER_ID='62')
    assert response.status_code == 403


@pytest.mark.django_db
def test_suggestions_plan_not_found(api_client, settings):
    settings.AUTH_SERVICE_URL = ''
    UserProfile.objects.create(user_id=63, daily_calories=2000)

    response = api_client.get('/plans/99999/suggestions/', HTTP_X_USER_ID='63')
    assert response.status_code == 404


@pytest.mark.django_db
def test_suggestions_without_api_key_returns_503(api_client, settings):
    settings.RECIPES_SERVICE_URL = 'http://recipes.test'
    settings.AUTH_SERVICE_URL = ''
    settings.MISTRAL_API_KEY = ''
    UserProfile.objects.create(user_id=64, daily_calories=2000)

    with patch.object(RecipesServiceClient, 'list_recipes', return_value=_three_recipes_2000_kcal()):
        create = api_client.post('/plans/generate/', HTTP_X_USER_ID='64')
    plan_id = create.data['id']

    response = api_client.get(f'/plans/{plan_id}/suggestions/', HTTP_X_USER_ID='64')
    assert response.status_code == 503
    assert response.data.get('error') == 'mistral_not_configured'


@pytest.mark.django_db
def test_suggestions_mistral_success_via_eager_celery(api_client, settings):
    settings.RECIPES_SERVICE_URL = 'http://recipes.test'
    settings.AUTH_SERVICE_URL = ''
    settings.MISTRAL_API_KEY = 'mist-test-not-real'
    UserProfile.objects.create(user_id=65, daily_calories=2000, excluded_ingredients='сахар')

    ai_json = (
        '{"summary": "Норма", "tips": ["больше овощей"], '
        '"possible_improvements": [], "warnings": []}'
    )
    with patch.object(RecipesServiceClient, 'list_recipes', return_value=_three_recipes_2000_kcal()):
        create = api_client.post('/plans/generate/', HTTP_X_USER_ID='65')
    plan_id = create.data['id']

    with patch.object(MistralClient, 'chat_completion', return_value=ai_json):
        response = api_client.get(f'/plans/{plan_id}/suggestions/', HTTP_X_USER_ID='65')

    assert response.status_code == 200
    assert response.data['suggestions']['summary'] == 'Норма'
    assert response.data['diversity_score'] >= 0.0
    assert response.data['model'] == settings.MISTRAL_MODEL


@pytest.mark.django_db
def test_suggestions_mistral_api_error_cached_502(api_client, settings):
    settings.RECIPES_SERVICE_URL = 'http://recipes.test'
    settings.AUTH_SERVICE_URL = ''
    settings.MISTRAL_API_KEY = 'mist-test-not-real'
    UserProfile.objects.create(user_id=66, daily_calories=2000)

    with patch.object(RecipesServiceClient, 'list_recipes', return_value=_three_recipes_2000_kcal()):
        create = api_client.post('/plans/generate/', HTTP_X_USER_ID='66')
    plan_id = create.data['id']

    with patch.object(
        MistralClient,
        'chat_completion',
        side_effect=MistralAPIError('rate limit'),
    ):
        response = api_client.get(f'/plans/{plan_id}/suggestions/', HTTP_X_USER_ID='66')

    assert response.status_code == 502
    assert response.data.get('error') == 'mistral_failed'


@pytest.mark.django_db
def test_integration_profile_generate_and_ai_suggestions(api_client, settings):
    """Сквозной сценарий: профиль → генерация плана → AI-подсказки (мок Mistral)."""
    settings.MOCK_RECIPES = True
    settings.RECIPES_SERVICE_URL = ''
    settings.AUTH_SERVICE_URL = ''
    settings.MISTRAL_API_KEY = 'mist-integration-mock'

    api_client.post(
        '/profiles/',
        data={'daily_calories': 2000},
        format='json',
        HTTP_X_USER_ID='100',
    )
    gen = api_client.post('/plans/generate/', HTTP_X_USER_ID='100')
    assert gen.status_code == 201
    plan_id = gen.data['id']

    ai_json = (
        '{"summary": "Ок", "tips": ["1", "2"], '
        '"possible_improvements": ["3"], "warnings": []}'
    )
    with patch.object(MistralClient, 'chat_completion', return_value=ai_json):
        sug = api_client.get(f'/plans/{plan_id}/suggestions/', HTTP_X_USER_ID='100')

    assert sug.status_code == 200
    assert len(sug.data['suggestions']['tips']) == 2
