from __future__ import annotations


def suggestions_cache_key(user_id: int, plan_id: int) -> str:
    """Ключ Redis для AI-подсказок (формат из ТЗ: meal_plan:<user>)."""
    return f'meal_plan:{user_id}:{plan_id}'
