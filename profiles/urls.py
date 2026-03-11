from django.urls import path
from .views import ProfileCreateView, ProfileMeView

urlpatterns = [
    path('', ProfileCreateView.as_view(), name='profile-create'),
    path('me/', ProfileMeView.as_view(), name='profile-me'),
]
