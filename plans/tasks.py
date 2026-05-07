from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings
from django.core.cache import cache

from profiles.models import UserProfile

from .clients.mistral import MistralAPIError, MistralClient
from .diversity import diversity_score
from .models import MealPlan
from .services.ai_prompts import build_suggestions_messages
from .services.suggestions_cache import suggestions_cache_key

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def generate_plan_suggestions(self, plan_id: int, user_id: int) -> dict:
    """
    Асинхронно запрашивает у Mistral рекомендации по плану и кладёт результат в Redis на 1 час.
    """
    key = suggestions_cache_key(user_id, plan_id)
    try:
        plan = MealPlan.objects.get(pk=plan_id, user_id=user_id)
    except MealPlan.DoesNotExist:
        logger.warning('MealPlan missing for suggestions: plan_id=%s user_id=%s', plan_id, user_id)
        payload = {'error': 'plan_not_found'}
        cache.set(key, payload, timeout=getattr(settings, 'AI_SUGGESTIONS_CACHE_TTL', 3600))
        return payload

    api_key = getattr(settings, 'MISTRAL_API_KEY', '') or ''
    if not str(api_key).strip():
        err = {
            'error': 'mistral_not_configured',
            'message': 'Задайте MISTRAL_API_KEY',
        }
        cache.set(key, err, timeout=getattr(settings, 'AI_SUGGESTIONS_CACHE_TTL', 3600))
        return err

    div = diversity_score(plan.payload)
    excluded = ''
    try:
        profile = UserProfile.objects.get(user_id=user_id)
        excluded = profile.excluded_ingredients or ''
    except UserProfile.DoesNotExist:
        pass

    messages = build_suggestions_messages(
        plan_payload=plan.payload,
        daily_calories_target=plan.daily_calories_target,
        diversity=div,
        excluded_hint=excluded,
    )

    client = MistralClient(
        api_key,
        base_url=getattr(settings, 'MISTRAL_API_BASE', 'https://api.mistral.ai/v1'),
        model=getattr(settings, 'MISTRAL_MODEL', 'mistral-small-latest'),
        timeout=float(getattr(settings, 'EXTERNAL_SERVICE_TIMEOUT', 120) or 120),
    )
    try:
        raw = client.chat_completion(messages)
    except MistralAPIError as exc:
        logger.exception('Mistral failed for plan %s', plan_id)
        err = {'error': 'mistral_failed', 'detail': str(exc)[:500]}
        cache.set(key, err, timeout=600)
        return err

    data = MistralClient.parse_json_suggestions(raw)
    out = {
        'suggestions': data,
        'diversity_score': div,
        'model': getattr(settings, 'MISTRAL_MODEL', 'mistral-small-latest'),
    }
    ttl = getattr(settings, 'AI_SUGGESTIONS_CACHE_TTL', 3600)
    cache.set(key, out, timeout=ttl)
    return out
