from rest_framework import generics, authentication, permissions, viewsets
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.settings import api_settings
from django.utils import timezone

from . import serializers
from .models import User, UserPreference, UserDevice


class CreateUserView(generics.CreateAPIView):
    """Create a new user in the system"""
    serializer_class = serializers.UserSerializer


class CreateTokenView(ObtainAuthToken):
    """Create a new auth token for user"""
    serializer_class = serializers.AuthTokenSerializer
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES


class ManageUserView(generics.RetrieveUpdateAPIView):
    """Manage the authenticated user"""
    serializer_class = serializers.UserSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        """Retrieve and return authenticated user"""
        return self.request.user


class UserViewSet(viewsets.ModelViewSet):
    """Manage users in the database"""
    serializer_class = serializers.UserSerializer
    queryset = User.objects.all()
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAdminUser,)


class UserPreferenceViewSet(viewsets.ModelViewSet):
    """Manage user preferences"""
    serializer_class = serializers.UserPreferenceSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        """Return preferences for authenticated user"""
        return UserPreference.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Create a new preference"""
        serializer.save(user=self.request.user)


class UserDeviceViewSet(viewsets.ModelViewSet):
    """Manage user devices"""
    serializer_class = serializers.UserDeviceSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        """Return devices for authenticated user"""
        return UserDevice.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Create a new device and update last used time"""
        serializer.save(user=self.request.user, last_used=timezone.now())

    def perform_update(self, serializer):
        """Update a device and its last used time"""
        serializer.save(last_used=timezone.now())
