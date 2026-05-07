from __future__ import annotations

from typing import Any


def build_suggestions_messages(
    *,
    plan_payload: dict[str, Any],
    daily_calories_target: int,
    diversity: float,
    excluded_hint: str = '',
) -> list[dict[str, str]]:
    """Сообщения для LLM (Mistral): просим строго JSON с советами по рациону."""
    user_block = (
        f'Цель калорий в день: {daily_calories_target} ккал.\n'
        f'Оценка разнообразия плана (0..1, выше — разнообразнее): {diversity}.\n'
    )
    if excluded_hint:
        user_block += f'Исключённые ингредиенты пользователя: {excluded_hint}\n'
    user_block += f'Текущий недельный план (JSON):\n{plan_payload}\n'

    system = (
        'Ты диетолог-консультант. По переданному плану питания дай краткие, практичные советы на русском. '
        'Ответь одним JSON-объектом без markdown и без текста вне JSON, со структурой:\n'
        '{"summary": "краткое резюме", "tips": ["совет1", "совет2"], '
        '"possible_improvements": ["улучшение1"], "warnings": ["предупреждение или пустой массив"]}\n'
        'Все строки на русском. Не выдумывай числа калорий для блюд, которых нет в плане.'
    )

    return [
        {'role': 'system', 'content': system},
        {'role': 'user', 'content': user_block},
    ]
