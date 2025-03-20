from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'tasks', views.MonitoringTaskViewSet)
router.register(r'configs', views.ProductMonitoringConfigViewSet)
router.register(r'results', views.MonitoringResultViewSet)
router.register(r'stats', views.MonitoringStatsViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
