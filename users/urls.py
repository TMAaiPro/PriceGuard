from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('profile', views.UserViewSet)
router.register('preferences', views.UserPreferenceViewSet)
router.register('devices', views.UserDeviceViewSet)

app_name = 'users'

urlpatterns = [
    path('create/', views.CreateUserView.as_view(), name='create'),
    path('login/', views.CreateTokenView.as_view(), name='login'),
    path('me/', views.ManageUserView.as_view(), name='me'),
    path('', include(router.urls)),
]
