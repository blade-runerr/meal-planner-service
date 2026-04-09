from __future__ import annotations

import logging
from typing import Optional

import requests
from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from profiles.models import UserProfile
from profiles.views import USER_ID_HEADER, get_user_id_from_request

from .clients import AuthServiceClient, RecipesServiceClient
from .mock_recipes import get_mock_recipes
from .models import MealPlan
from .serializers import MealPlanSerializer
from .services.plan_generator import build_week_payload

logger = logging.getLogger(__name__)


def get_recipes_client() -> Optional[RecipesServiceClient]:
    """Клиент recipes-service или None, если RECIPES_SERVICE_URL не задан."""
    base = getattr(settings, 'RECIPES_SERVICE_URL', '') or ''
    if not base:
        return None
    timeout = getattr(settings, 'EXTERNAL_SERVICE_TIMEOUT', 10.0)
    return RecipesServiceClient(base, timeout=timeout)


def get_auth_client() -> Optional[AuthServiceClient]:
    """Клиент auth-service или None, если AUTH_SERVICE_URL не задан (проверка пользователя пропускается)."""
    base = getattr(settings, 'AUTH_SERVICE_URL', '') or ''
    if not base:
        return None
    timeout = getattr(settings, 'EXTERNAL_SERVICE_TIMEOUT', 10.0)
    return AuthServiceClient(base, timeout=timeout)


class PlanGenerateView(APIView):

    @extend_schema(
        summary='Сгенерировать рацион на неделю',
        responses={201: MealPlanSerializer, 400: None, 404: None, 502: None, 503: None},
        parameters=[USER_ID_HEADER],
    )
    def post(self, request):
        """Собирает недельный план, сохраняет MealPlan; требуется X-User-Id и существующий профиль."""
        user_id, error_response = get_user_id_from_request(request)
        if error_response:
            return error_response

        auth_client = get_auth_client()
        if auth_client is not None:
            try:
                if not auth_client.user_exists(user_id):
                    return Response(
                        {'error': 'Пользователь не найден в auth-service'},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            except requests.RequestException as exc:
                logger.exception('auth-service недоступен')
                return Response(
                    {'error': 'auth-service недоступен', 'detail': str(exc)},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

        try:
            profile = UserProfile.objects.get(user_id=user_id)
        except UserProfile.DoesNotExist:
            return Response(
                {'error': 'Сначала создайте профиль (POST /profiles/)'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if getattr(settings, 'MOCK_RECIPES', False):
            raw_recipes = get_mock_recipes()
        else:
            recipes_client = get_recipes_client()
            if recipes_client is None:
                return Response(
                    {
                        'error': (
                            'Не задан RECIPES_SERVICE_URL. Для автономной разработки задайте MOCK_RECIPES=1 '
                            'или укажите URL recipes-service.'
                        ),
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            try:
                raw_recipes = recipes_client.list_recipes()
            except requests.RequestException as exc:
                logger.exception('recipes-service недоступен')
                return Response(
                    {'error': 'recipes-service недоступен', 'detail': str(exc)},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

        try:
            payload = build_week_payload(
                raw_recipes,
                profile.daily_calories,
                profile.excluded_ingredients,
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        plan = MealPlan.objects.create(
            user_id=user_id,
            daily_calories_target=profile.daily_calories,
            payload=payload,
        )
        return Response(MealPlanSerializer(plan).data, status=status.HTTP_201_CREATED)


class PlanDetailView(APIView):

    @extend_schema(
        summary='Получить план по id',
        responses={200: MealPlanSerializer, 403: None, 404: None},
        parameters=[USER_ID_HEADER],
    )
    def get(self, request, plan_id: int):
        """Возвращает план по id только если X-User-Id совпадает с владельцем плана."""
        user_id, error_response = get_user_id_from_request(request)
        if error_response:
            return error_response

        try:
            plan = MealPlan.objects.get(pk=plan_id)
        except MealPlan.DoesNotExist:
            return Response({'error': 'План не найден'}, status=status.HTTP_404_NOT_FOUND)

        if plan.user_id != user_id:
            return Response({'error': 'Доступ к чужому плану запрещён'}, status=status.HTTP_403_FORBIDDEN)

        return Response(MealPlanSerializer(plan).data)
