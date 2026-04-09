"""Статичные рецепты для разработки без recipes-service (тот же формат, что ожидает генератор)."""


def get_mock_recipes():
    return [
        {
            'id': 1,
            'name': 'Овсянка с ягодами',
            'tags': [{'id': 1, 'name': 'завтрак'}],
            'ingredients': [{'id': 101, 'name': 'овсянка'}, {'id': 102, 'name': 'ягоды'}],
            'calories': 650,
        },
        {
            'id': 2,
            'name': 'Курица с гречкой',
            'tags': [{'id': 2, 'name': 'обед'}],
            'ingredients': [{'id': 103, 'name': 'курица'}, {'id': 104, 'name': 'гречка'}],
            'calories': 650,
        },
        {
            'id': 3,
            'name': 'Рыба с овощами',
            'tags': [{'id': 3, 'name': 'ужин'}],
            'ingredients': [{'id': 105, 'name': 'рыба'}, {'id': 106, 'name': 'овощи'}],
            'calories': 700,
        },
    ]
