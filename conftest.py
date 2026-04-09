def pytest_configure():
    import os

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meal_planner_service.settings_test')
    import django

    django.setup()
