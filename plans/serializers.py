from rest_framework import serializers

from .models import MealPlan


class MealPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = MealPlan
        fields = ['id', 'user_id', 'daily_calories_target', 'payload', 'created_at', 'updated_at']
        read_only_fields = fields
