from django.urls import path

from .views import PlanDetailView, PlanGenerateView

urlpatterns = [
    path('generate/', PlanGenerateView.as_view(), name='plan-generate'),
    path('<int:plan_id>/', PlanDetailView.as_view(), name='plan-detail'),
]
