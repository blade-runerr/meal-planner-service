from django.db import models


class MealPlan(models.Model):
    """Сохранённый недельный рацион: владелец по user_id (из X-User-Id), тело плана в payload (JSON)."""

    user_id = models.IntegerField(db_index=True)
    daily_calories_target = models.PositiveIntegerField()
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'meal_plans'
        ordering = ['-created_at']

    def __str__(self):
        return f'MealPlan(id={self.pk}, user_id={self.user_id})'
