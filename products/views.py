from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import timedelta
from rest_framework import viewsets, generics, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Product, Retailer, Category, ProductPrice, UserProduct
from .serializers import (
    ProductSerializer, ProductListSerializer, RetailerSerializer,
    CategorySerializer, ProductPriceSerializer, UserProductSerializer
)


class ProductViewSet(viewsets.ModelViewSet):
    """Viewset for products"""
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['retailer', 'categories', 'is_active']
    search_fields = ['name', 'description', 'sku', 'upc']
    ordering_fields = ['current_price', 'name', 'last_checked']
    
    def get_serializer_class(self):
        """Return appropriate serializer class"""
        if self.action == 'list':
            return ProductListSerializer
        return self.serializer_class
    
    @action(detail=True, methods=['post'])
    def track(self, request, pk=None):
        """Add a product to user's tracked products"""
        product = self.get_object()
        user = request.user
        
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=401)
            
        # Check if already tracking this product
        existing = UserProduct.objects.filter(user=user, product=product).first()
        if existing:
            return Response({"error": "Already tracking this product"}, status=400)
            
        # Create new tracking
        tracking = UserProduct.objects.create(
            user=user,
            product=product,
            target_price=request.data.get('target_price'),
            notify_price_drop=request.data.get('notify_price_drop', True),
            notify_availability=request.data.get('notify_availability', False)
        )
        
        serializer = UserProductSerializer(tracking)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def price_history(self, request, pk=None):
        """Return price history for a product"""
        product = self.get_object()
        days = request.query_params.get('days', 30)
        
        try:
            days = int(days)
        except ValueError:
            days = 30
            
        since = timezone.now() - timedelta(days=days)
        prices = product.prices.filter(timestamp__gte=since)
        
        serializer = ProductPriceSerializer(prices, many=True)
        return Response(serializer.data)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Viewset for categories"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    
    @action(detail=True)
    def products(self, request, pk=None):
        """Return products for a category"""
        category = self.get_object()
        products = Product.objects.filter(categories=category)
        
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = ProductListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
            
        serializer = ProductListSerializer(products, many=True)
        return Response(serializer.data)


class RetailerViewSet(viewsets.ReadOnlyModelViewSet):
    """Viewset for retailers"""
    queryset = Retailer.objects.all()
    serializer_class = RetailerSerializer
    
    @action(detail=True)
    def products(self, request, pk=None):
        """Return products for a retailer"""
        retailer = self.get_object()
        products = Product.objects.filter(retailer=retailer)
        
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = ProductListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
            
        serializer = ProductListSerializer(products, many=True)
        return Response(serializer.data)


class ProductPriceViewSet(viewsets.ReadOnlyModelViewSet):
    """Viewset for product price history"""
    queryset = ProductPrice.objects.all()
    serializer_class = ProductPriceSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['product']


class UserProductViewSet(viewsets.ModelViewSet):
    """Viewset for user's tracked products"""
    serializer_class = UserProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Return user's tracked products"""
        return UserProduct.objects.filter(user=self.request.user)


class ProductSearchView(generics.ListAPIView):
    """Advanced search endpoint for products"""
    serializer_class = ProductListSerializer
    
    def get_queryset(self):
        """Return search results"""
        queryset = Product.objects.all()
        query = self.request.query_params.get('q', None)
        
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(sku__icontains=query) |
                Q(upc__icontains=query)
            )
            
        # Apply filters if provided
        categories = self.request.query_params.get('categories', None)
        if categories:
            category_ids = [int(id) for id in categories.split(',') if id.isdigit()]
            queryset = queryset.filter(categories__id__in=category_ids)
            
        retailers = self.request.query_params.get('retailers', None)
        if retailers:
            retailer_ids = [int(id) for id in retailers.split(',') if id.isdigit()]
            queryset = queryset.filter(retailer__id__in=retailer_ids)
            
        min_price = self.request.query_params.get('min_price', None)
        if min_price and min_price.isdigit():
            queryset = queryset.filter(current_price__gte=float(min_price))
            
        max_price = self.request.query_params.get('max_price', None)
        if max_price and max_price.isdigit():
            queryset = queryset.filter(current_price__lte=float(max_price))
            
        return queryset


class ProductPriceAlertView(generics.ListAPIView):
    """View for products with recent price drops"""
    serializer_class = ProductListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Return products with price drops"""
        # Products where current price is less than the average of the last 7 days
        days_ago = timezone.now() - timedelta(days=7)
        products_with_drops = []
        
        # Get user's tracked products
        user_products = UserProduct.objects.filter(
            user=self.request.user,
            notify_price_drop=True
        ).select_related('product')
        
        for user_product in user_products:
            product = user_product.product
            
            # Get price history
            price_history = product.prices.filter(timestamp__gte=days_ago)
            if price_history.count() < 2:  # Need at least 2 data points
                continue
                
            # Calculate average
            avg_price = price_history.aggregate(Avg('price'))['price__avg']
            
            # Check if current price is lower than average
            if product.current_price < avg_price:
                # If target price is set, check if current price is below target
                if user_product.target_price and product.current_price <= user_product.target_price:
                    products_with_drops.append(product)
                # If no target price, include anyway
                elif not user_product.target_price:
                    products_with_drops.append(product)
                    
        return products_with_drops


class PopularProductsView(generics.ListAPIView):
    """View for popular products"""
    serializer_class = ProductListSerializer
    
    def get_queryset(self):
        """Return most tracked products"""
        return Product.objects.annotate(
            track_count=Count('tracking_users')
        ).order_by('-track_count')[:10]


class RecentProductsView(generics.ListAPIView):
    """View for recently added or updated products"""
    serializer_class = ProductListSerializer
    
    def get_queryset(self):
        """Return recently added/updated products"""
        return Product.objects.order_by('-updated_at')[:10]
