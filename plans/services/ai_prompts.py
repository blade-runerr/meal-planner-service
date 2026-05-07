from __future__ import annotations

import json
from typing import Any

# Чтобы не раздувать запрос к API и не ловить обрывы соединения на больших телах.
_MAX_PLAN_JSON_CHARS = 14_000


def _slim_plan_for_llm(plan_payload: dict[str, Any]) -> dict[str, Any]:
    """Компактное представление недели: только день, сумма ккал и блюда без лишних полей."""
    slim_days = []
    for d in plan_payload.get('days') or []:
        slim_days.append(
            {
                'day': d.get('day_index'),
                'kcal': d.get('total_calories'),
                'meals': [
                    {'name': m.get('recipe_name'), 'cal': m.get('calories')}
                    for m in d.get('meals') or []
                ],
            }
        )
    return {
        'daily_target': plan_payload.get('daily_target'),
        'meals_per_day': plan_payload.get('meals_per_day'),
        'days': slim_days,
    }


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

    slim = _slim_plan_for_llm(plan_payload)
    plan_txt = json.dumps(slim, ensure_ascii=False, separators=(',', ':'))
    if len(plan_txt) > _MAX_PLAN_JSON_CHARS:
        plan_txt = plan_txt[: _MAX_PLAN_JSON_CHARS] + '…'

    user_block += f'Недельный план (компактный JSON):\n{plan_txt}\n'

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
