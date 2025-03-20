from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('', views.AlertViewSet)
router.register('types', views.AlertTypeViewSet)
router.register('configs', views.AlertConfigurationViewSet)

app_name = 'alerts'

urlpatterns = [
    path('summary/', views.AlertSummaryView.as_view(), name='summary'),
    path('mark-all-read/', views.MarkAllAlertsReadView.as_view(), name='mark-all-read'),
    path('', include(router.urls)),
]
