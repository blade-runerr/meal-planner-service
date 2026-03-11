from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import UserProfile
from .serializers import UserProfileSerializer


def get_user_id_from_request(request):
    """Extract user_id from X-User-Id header (set by auth-service / API gateway)."""
    user_id = request.headers.get('X-User-Id')
    if user_id is None:
        return None, Response(
            {'error': 'X-User-Id header is required'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        return int(user_id), None
    except ValueError:
        return None, Response(
            {'error': 'X-User-Id must be an integer'},
            status=status.HTTP_400_BAD_REQUEST,
        )


class ProfileCreateView(APIView):
    """POST /profiles — create or update user profile settings."""

    def post(self, request):
        user_id, error_response = get_user_id_from_request(request)
        if error_response:
            return error_response

        profile, created = UserProfile.objects.get_or_create(user_id=user_id)
        serializer = UserProfileSerializer(profile, data=request.data, partial=not created)
        if serializer.is_valid():
            serializer.save(user_id=user_id)
            http_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            return Response(serializer.data, status=http_status)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileMeView(APIView):
    """GET /profiles/me — retrieve current user profile."""

    def get(self, request):
        user_id, error_response = get_user_id_from_request(request)
        if error_response:
            return error_response

        try:
            profile = UserProfile.objects.get(user_id=user_id)
        except UserProfile.DoesNotExist:
            return Response(
                {'error': 'Profile not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)
