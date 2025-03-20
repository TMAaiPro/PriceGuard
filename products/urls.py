from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('', views.ProductViewSet)
router.register('categories', views.CategoryViewSet)
router.register('retailers', views.RetailerViewSet)
router.register('tracked', views.UserProductViewSet)
router.register('prices', views.ProductPriceViewSet)

app_name = 'products'

urlpatterns = [
    path('search/', views.ProductSearchView.as_view(), name='product-search'),
    path('price-alerts/', views.ProductPriceAlertView.as_view(), name='price-alerts'),
    path('popular/', views.PopularProductsView.as_view(), name='popular'),
    path('recent/', views.RecentProductsView.as_view(), name='recent'),
    path('', include(router.urls)),
]
