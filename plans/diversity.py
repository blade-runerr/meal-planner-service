"""Метрика разнообразия рациона по сохранённому payload плана (без полных тегов/ингредиентов в JSON)."""


def diversity_score(payload: dict) -> float:
    """
    Оценка 0..1: насколько план разнообразен по смене блюд.
    Комбинирует долю уникальных recipe_id и долю «переходов», где соседние приёмы — разные блюда.
    """
    days = payload.get('days') or []
    ordered_ids: list[int] = []
    for day in sorted(days, key=lambda d: d.get('day_index', 0)):
        for meal in day.get('meals') or []:
            rid = meal.get('recipe_id')
            if rid is not None:
                ordered_ids.append(int(rid))

    n = len(ordered_ids)
    if n == 0:
        return 0.0
    if n == 1:
        return 1.0

    unique_ratio = len(set(ordered_ids)) / n
    transitions = sum(1 for i in range(n - 1) if ordered_ids[i] != ordered_ids[i + 1])
    edge_ratio = transitions / (n - 1)

    return round(0.5 * unique_ratio + 0.5 * edge_ratio, 4)
