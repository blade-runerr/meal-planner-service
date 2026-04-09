from django.db import models


class UserProfile(models.Model):
    user_id = models.IntegerField(unique=True)
    daily_calories = models.PositiveIntegerField(default=2000)
    excluded_ingredients = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_profiles'

    def __str__(self):
        return f'UserProfile(user_id={self.user_id}, daily_calories={self.daily_calories})'
#вынести аллергены в другую таблицу