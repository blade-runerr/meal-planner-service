from __future__ import annotations

import copy
from typing import Any

from plans.similarity import calculate_similarity

DAYS_IN_WEEK = 7
MEALS_PER_DAY = 3
CAL_LOW = 0.68
CAL_HIGH = 1.32


def parse_excluded_ingredients(raw: str) -> set[str]:
    if not raw or not str(raw).strip():
        return set()
    return {s.strip().lower() for s in str(raw).split(',') if s.strip()}


def _flatten_ingredient(ing: Any) -> dict[str, Any]:
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
    if target <= 0:
        return False
    lo = int(target * CAL_LOW)
    hi = int(target * CAL_HIGH) + 1
    return lo <= total <= hi


def build_week_payload(
    recipes: list[dict[str, Any]],
    daily_calories: int,
    excluded_raw: str,
) -> dict[str, Any]:
    excluded = parse_excluded_ingredients(excluded_raw)
    pool = filter_recipes(recipes, excluded)
    if not pool:
        raise ValueError('После фильтра исключённых ингредиентов не осталось рецептов')

    days_out: list[dict[str, Any]] = []
    for day_index in range(1, DAYS_IN_WEEK + 1):
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
                raise ValueError(f'Не удалось подобрать приёмы пищи для дня {day_index}')

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
            raise ValueError(
                f'Калорийность дня {day_index} ({total} ккал) вне допуска от цели {daily_calories} ккал'
            )

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
