from __future__ import annotations


def suggestions_cache_key(user_id: int, plan_id: int) -> str:
    """Ключ Redis для AI-подсказок. :sugg_v2 — смена префикса сбрасывает старый кеш с коротким таймаутом."""
    return f'meal_plan:{user_id}:{plan_id}:sugg_v3'
