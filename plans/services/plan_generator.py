from __future__ import annotations

import copy
import itertools
from typing import Any

from plans.similarity import calculate_similarity

DAYS_IN_WEEK = 7
MEALS_PER_DAY = 3
CAL_LOW = 0.68
CAL_HIGH = 1.32
# Перебор комбинаций за день, если жадный алгоритм застрял (у моков 3 рецепта — дёшево).
_MAX_POOL_BRUTE_FORCE = 24


def parse_excluded_ingredients(raw: str) -> set[str]:
    """Строка профиля «ингредиент1, ингредиент2» → множество имён в нижнем регистре."""
    if not raw or not str(raw).strip():
        return set()
    return {s.strip().lower() for s in str(raw).split(',') if s.strip()}


def _flatten_ingredient(ing: Any) -> dict[str, Any]:
    """Приводит элемент ingredients API к виду {id, name} (учёт вложенного объекта ingredient)."""
    if not isinstance(ing, dict):
        return {'id': None, 'name': str(ing)}
    inner = ing.get('ingredient')
    if isinstance(inner, dict):
        return {
            'id': inner.get('id'),
            'name': inner.get('name', ''),
        }
    return {
        'id': ing.get('id'),
        'name': ing.get('name', ''),
    }


def normalize_recipe(raw: dict[str, Any]) -> dict[str, Any]:
    """Копия рецепта с плоскими ингредиентами и полем calories."""
    r = copy.deepcopy(raw)
    tags = r.get('tags') or []
    ingredients_raw = r.get('ingredients') or []
    ingredients = [_flatten_ingredient(x) for x in ingredients_raw]
    cooking_time = int(r.get('cooking_time') or 0)
    calories = r.get('calories')
    if calories is None:
        calories = max(200, min(900, cooking_time * 8 + 250))
    else:
        calories = int(calories)
    return {
        'id': r['id'],
        'name': r.get('name', ''),
        'tags': tags,
        'ingredients': ingredients,
        'calories': calories,
    }


def recipe_matches_exclusion(recipe: dict[str, Any], excluded: set[str]) -> bool:
    """True, если у рецепта есть ингредиент с именем или строковым id из множества excluded."""
    if not excluded:
        return False
    for ing in recipe.get('ingredients') or []:
        name = str(ing.get('name') or '').strip().lower()
        iid = ing.get('id')
        sid = str(iid) if iid is not None else ''
        if name and name in excluded:
            return True
        if sid and sid in excluded:
            return True
    return False


def filter_recipes(recipes: list[dict[str, Any]], excluded: set[str]) -> list[dict[str, Any]]:
    """Нормализованные рецепты с id, не попадающие под исключения по ингредиентам."""
    out = []
    for raw in recipes:
        if 'id' not in raw:
            continue
        norm = normalize_recipe(raw)
        if recipe_matches_exclusion(norm, excluded):
            continue
        out.append(norm)
    return out


def day_calories_ok(total: int, target: int) -> bool:
    """Проверка суммы ккал за день на попадание в коридор [CAL_LOW·target, CAL_HIGH·target]."""
    if target <= 0:
        return False
    lo = int(target * CAL_LOW)
    hi = int(target * CAL_HIGH) + 1
    return lo <= total <= hi


def _greedy_day_meals(pool: list[dict[str, Any]], daily_calories: int) -> list[dict[str, Any]] | None:
    """Жадный подбор MEALS_PER_DAY приёмов; None если застряли или сумма вне допуска."""
    meals: list[dict[str, Any]] = []
    remaining = daily_calories
    prev_recipe = None

    for meal_slot in range(MEALS_PER_DAY):
        slots_left = MEALS_PER_DAY - meal_slot
        soft_target = max(remaining // slots_left, 1)

        best = None
        best_key = None

        for cand in pool:
            cal = cand['calories']
            if cal > remaining:
                continue
            if prev_recipe is not None:
                sim = calculate_similarity(prev_recipe, cand)
                diversity = 1.0 - sim
            else:
                diversity = 1.0
            over = max(0, cal - soft_target)
            key = (diversity, -over, cal)
            if best_key is None or key > best_key:
                best = cand
                best_key = key

        if best is None:
            for cand in sorted(pool, key=lambda x: x['calories']):
                if cand['calories'] <= remaining:
                    best = cand
                    break

        if best is None:
            return None

        meals.append(
            {
                'recipe_id': best['id'],
                'recipe_name': best['name'],
                'calories': best['calories'],
            }
        )
        remaining -= best['calories']
        prev_recipe = best

    total = sum(m['calories'] for m in meals)
    if not day_calories_ok(total, daily_calories):
        return None
    return meals


def _brute_force_day_meals(pool: list[dict[str, Any]], daily_calories: int) -> list[dict[str, Any]]:
    """Подбор дня полным перебором |pool|^3 (только для малого пула)."""
    if len(pool) > _MAX_POOL_BRUTE_FORCE:
        raise ValueError(
            f'Слишком много рецептов ({len(pool)}) для надёжного подбора без расширенного планировщика'
        )
    lo = int(daily_calories * CAL_LOW)
    hi = int(daily_calories * CAL_HIGH) + 1

    best_combo: tuple[dict[str, Any], ...] | None = None
    best_key: tuple[float, int] | None = None

    for combo in itertools.product(pool, repeat=MEALS_PER_DAY):
        total = sum(c['calories'] for c in combo)
        if not (lo <= total <= hi):
            continue
        div = 0.0
        prev = None
        for cand in combo:
            if prev is not None:
                div += 1.0 - calculate_similarity(prev, cand)
            prev = cand
        key = (div, total)
        if best_key is None or key > best_key:
            best_key = key
            best_combo = combo

    if best_combo is None:
        raise ValueError(
            f'Невозможно набрать день из доступных рецептов в допуске '
            f'{CAL_LOW:.0%}–{CAL_HIGH:.0%} от цели {daily_calories} ккал'
        )

    return [
        {'recipe_id': c['id'], 'recipe_name': c['name'], 'calories': c['calories']}
        for c in best_combo
    ]


def build_week_payload(
    recipes: list[dict[str, Any]],
    daily_calories: int,
    excluded_raw: str,
) -> dict[str, Any]:
    """Строит JSON-план: 7 дней по 3 приёма пищи с учётом исключений, ккал и разнообразия блюд."""
    excluded = parse_excluded_ingredients(excluded_raw)
    pool = filter_recipes(recipes, excluded)
    if not pool:
        raise ValueError('После фильтра исключённых ингредиентов не осталось рецептов')

    days_out: list[dict[str, Any]] = []
    for day_index in range(1, DAYS_IN_WEEK + 1):
        meals: list[dict[str, Any]] | None = _greedy_day_meals(pool, daily_calories)
        if meals is None:
            try:
                meals = _brute_force_day_meals(pool, daily_calories)
            except ValueError as exc:
                raise ValueError(f'Не удалось подобрать приёмы пищи для дня {day_index}: {exc}') from exc

        total = sum(m['calories'] for m in meals)

        days_out.append(
            {
                'day_index': day_index,
                'meals': meals,
                'total_calories': total,
            }
        )

    return {
        'version': 1,
        'days': days_out,
        'daily_target': daily_calories,
        'meals_per_day': MEALS_PER_DAY,
    }
