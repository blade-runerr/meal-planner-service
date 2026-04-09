"""Сходство рецептов по пересечению тегов и ингредиентов (Jaccard)."""


def _norm_item(item, kind: str):
    """Возвращает ключ для множества сходства: тег или ингредиент по id либо по имени."""
    if not isinstance(item, dict):
        return (kind, str(item))
    if item.get('id') is not None:
        return (kind, 'id', int(item['id']))
    name = item.get('name')
    if name:
        return (kind, 'name', str(name).strip().lower())
    return None


def _signature(recipe: dict) -> set:
    """Множество нормализованных тегов и ингредиентов рецепта (включая вложенный ключ ingredient)."""
    sig = set()
    for t in recipe.get('tags') or []:
        key = _norm_item(t, 't')
        if key:
            sig.add(key)
    for ing in recipe.get('ingredients') or []:
        key = _norm_item(ing, 'i')
        if key:
            sig.add(key)
        inner = ing.get('ingredient') if isinstance(ing, dict) else None
        if isinstance(inner, dict):
            key = _norm_item(inner, 'i')
            if key:
                sig.add(key)
    return sig


def calculate_similarity(recipe1: dict, recipe2: dict) -> float:
    """Коэффициент Жаккара по объединённым множествам тегов и ингредиентов; 0..1, у пустых обоих — 1.0."""
    a = _signature(recipe1)
    b = _signature(recipe2)
    if not a and not b:
        return 1.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0
