from django.contrib import admin

from .models import MealPlan


@admin.register(MealPlan)
class MealPlanAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_id', 'daily_calories_target', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
