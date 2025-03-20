from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('insights', views.PriceInsightViewSet)
router.register('predictions', views.PricePredictionViewSet)
router.register('events', views.UserAnalyticsViewSet)

app_name = 'analytics'

urlpatterns = [
    path('dashboard/', views.UserDashboardView.as_view(), name='dashboard'),
    path('tracking-stats/', views.TrackingStatsView.as_view(), name='tracking-stats'),
    path('track-event/', views.TrackEventView.as_view(), name='track-event'),
    path('product-trends/<int:product_id>/', views.ProductTrendsView.as_view(), name='product-trends'),
    path('retailer-trends/<int:retailer_id>/', views.RetailerTrendsView.as_view(), name='retailer-trends'),
    path('price-prediction/<int:product_id>/', views.PricePredictionView.as_view(), name='price-prediction'),
    path('', include(router.urls)),
]
