from rest_framework import serializers

from .diversity import diversity_score
from .models import MealPlan


class MealPlanSerializer(serializers.ModelSerializer):
    """Сериализация сохранённого плана для ответов POST /plans/generate/ и GET /plans/<id>/."""

    diversity_score = serializers.SerializerMethodField()

    class Meta:
        model = MealPlan
        fields = [
            'id',
            'user_id',
            'daily_calories_target',
            'payload',
            'diversity_score',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_diversity_score(self, obj: MealPlan) -> float:
        return diversity_score(obj.payload or {})
