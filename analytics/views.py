from django.db import connection
from django.db.models import Count, Avg, Max, Min, F, Sum, Q
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
import pandas as pd

from .models import PriceInsight, PricePrediction, UserAnalytics
from .serializers import (
    PriceInsightSerializer, PricePredictionSerializer,
    UserAnalyticsSerializer, UserAnalyticsEventSerializer
)
from products.models import Product, ProductPrice, Retailer, UserProduct


class PriceInsightViewSet(viewsets.ReadOnlyModelViewSet):
    """Viewset for price insights"""
    serializer_class = PriceInsightSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['product', 'insight_type']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Return insights for products the user has access to"""
        # Get products that the user is tracking
        tracked_products = UserProduct.objects.filter(
            user=self.request.user
        ).values_list('product_id', flat=True)
        
        return PriceInsight.objects.filter(
            product_id__in=tracked_products
        )


class PricePredictionViewSet(viewsets.ReadOnlyModelViewSet):
    """Viewset for price predictions"""
    serializer_class = PricePredictionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['product', 'prediction_date']
    ordering_fields = ['prediction_date', 'created_at']
    ordering = ['-prediction_date']
    
    def get_queryset(self):
        """Return predictions for products the user has access to"""
        # Get products that the user is tracking
        tracked_products = UserProduct.objects.filter(
            user=self.request.user
        ).values_list('product_id', flat=True)
        
        return PricePrediction.objects.filter(
            product_id__in=tracked_products
        )


class UserAnalyticsViewSet(viewsets.ModelViewSet):
    """Viewset for user analytics events"""
    serializer_class = UserAnalyticsSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['action_type', 'product']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Return only the current user's analytics events"""
        if self.request.user.is_staff:
            # Staff can see all events for support purposes
            return UserAnalytics.objects.all()
        return UserAnalytics.objects.filter(user=self.request.user)


class TrackEventView(APIView):
    """View for tracking user events"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, format=None):
        """Track a user event"""
        serializer = UserAnalyticsEventSerializer(data=request.data)
        if serializer.is_valid():
            # Add user info
            serializer.save(
                user=request.user,
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class UserDashboardView(APIView):
    """View for user dashboard data"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, format=None):
        """Return dashboard data for the user"""
        user = request.user
        
        # Get tracked products count
        tracked_count = UserProduct.objects.filter(user=user).count()
        
        # Get products with price drops
        price_drop_count = 0
        saved_amount = 0
        
        tracked_products = UserProduct.objects.filter(
            user=user
        ).select_related('product')
        
        for up in tracked_products:
            product = up.product
            # Get the highest price recorded for this product
            highest_price = ProductPrice.objects.filter(
                product=product,
                timestamp__gte=timezone.now() - timedelta(days=30)
            ).aggregate(Max('price'))['price__max']
            
            if highest_price and highest_price > product.current_price:
                price_drop_count += 1
                saved_amount += highest_price - product.current_price
        
        # Get recent insights
        tracked_product_ids = tracked_products.values_list('product_id', flat=True)
        recent_insights = PriceInsight.objects.filter(
            product_id__in=tracked_product_ids
        ).order_by('-created_at')[:5]
        
        insight_serializer = PriceInsightSerializer(recent_insights, many=True)
        
        return Response({
            'tracked_products': tracked_count,
            'price_drops': price_drop_count,
            'saved_amount': float(saved_amount),
            'recent_insights': insight_serializer.data,
        })


class TrackingStatsView(APIView):
    """View for tracking statistics"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, format=None):
        """Return tracking statistics for the user"""
        user = request.user
        
        # Get analytics data
        one_month_ago = timezone.now() - timedelta(days=30)
        
        # Product views
        product_views = UserAnalytics.objects.filter(
            user=user,
            action_type='view',
            created_at__gte=one_month_ago
        ).values('product__name').annotate(
            view_count=Count('id')
        ).order_by('-view_count')[:10]
        
        # Most tracked categories
        tracked_categories = UserProduct.objects.filter(
            user=user
        ).values(
            'product__categories__name'
        ).exclude(
            product__categories__name=None
        ).annotate(
            category_count=Count('id')
        ).order_by('-category_count')[:5]
        
        # Average price drop rate
        tracked_product_ids = UserProduct.objects.filter(
            user=user
        ).values_list('product_id', flat=True)
        
        # Get recent price insights for tracked products
        price_trends = PriceInsight.objects.filter(
            product_id__in=tracked_product_ids,
            insight_type='trend',
            created_at__gte=one_month_ago
        )
        
        downward_trends = price_trends.filter(
            data__trend_type='downward'
        ).count()
        
        upward_trends = price_trends.filter(
            data__trend_type='upward'
        ).count()
        
        stable_trends = price_trends.filter(
            data__trend_type='stable'
        ).count()
        
        total_trends = price_trends.count()
        
        return Response({
            'most_viewed_products': list(product_views),
            'top_categories': list(tracked_categories),
            'price_trends': {
                'downward': downward_trends,
                'upward': upward_trends,
                'stable': stable_trends,
                'total': total_trends,
                'downward_pct': (downward_trends / total_trends * 100) if total_trends > 0 else 0,
                'upward_pct': (upward_trends / total_trends * 100) if total_trends > 0 else 0,
                'stable_pct': (stable_trends / total_trends * 100) if total_trends > 0 else 0,
            }
        })


class ProductTrendsView(APIView):
    """View for product price trends"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, product_id, format=None):
        """Return trend data for a specific product"""
        # Check if user is tracking this product
        user = request.user
        product = get_object_or_404(Product, id=product_id)
        
        is_tracking = UserProduct.objects.filter(
            user=user, product=product
        ).exists()
        
        if not is_tracking and not user.is_staff:
            return Response(
                {"error": "You are not tracking this product"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get price history
        prices = ProductPrice.objects.filter(
            product=product
        ).order_by('timestamp')
        
        # Format data for response
        price_data = [
            {
                'date': p.timestamp.strftime('%Y-%m-%d'),
                'price': float(p.price)
            }
            for p in prices
        ]
        
        # Get insights for this product
        insights = PriceInsight.objects.filter(
            product=product
        ).order_by('-created_at')
        
        insight_serializer = PriceInsightSerializer(insights, many=True)
        
        return Response({
            'product_name': product.name,
            'current_price': float(product.current_price),
            'price_history': price_data,
            'insights': insight_serializer.data
        })


class RetailerTrendsView(APIView):
    """View for retailer price trends"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, retailer_id, format=None):
        """Return trend data for a specific retailer"""
        retailer = get_object_or_404(Retailer, id=retailer_id)
        user = request.user
        
        # Get tracked products from this retailer
        tracked_products = UserProduct.objects.filter(
            user=user,
            product__retailer=retailer
        ).values_list('product_id', flat=True)
        
        # Get price data for tracked products
        products_data = []
        
        for product_id in tracked_products:
            product = Product.objects.get(id=product_id)
            
            # Get last 30 days of price data
            thirty_days_ago = timezone.now() - timedelta(days=30)
            prices = ProductPrice.objects.filter(
                product=product,
                timestamp__gte=thirty_days_ago
            ).order_by('timestamp')
            
            # Calculate basic stats
            if prices.exists():
                first_price = prices.first().price
                last_price = prices.last().price
                price_change = last_price - first_price
                price_change_pct = (price_change / first_price * 100) if first_price > 0 else 0
                
                products_data.append({
                    'product_id': product.id,
                    'product_name': product.name,
                    'current_price': float(product.current_price),
                    'price_change': float(price_change),
                    'price_change_pct': float(price_change_pct),
                    'data_points': prices.count()
                })
        
        return Response({
            'retailer_name': retailer.name,
            'retailer_website': retailer.website,
            'tracked_products': len(products_data),
            'products': products_data
        })


class PricePredictionView(APIView):
    """View for predicting future product prices"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, product_id, format=None):
        """Return price prediction for a product"""
        # Check if user is tracking this product
        user = request.user
        product = get_object_or_404(Product, id=product_id)
        
        is_tracking = UserProduct.objects.filter(
            user=user, product=product
        ).exists()
        
        if not is_tracking and not user.is_staff:
            return Response(
                {"error": "You are not tracking this product"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get historical price data
        prices = ProductPrice.objects.filter(
            product=product
        ).order_by('timestamp')
        
        # Need at least 10 data points for prediction
        if prices.count() < 10:
            return Response(
                {"error": "Not enough historical data for prediction"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Prepare data for model
        dates = [(p.timestamp - prices.first().timestamp).days for p in prices]
        price_values = [float(p.price) for p in prices]
        
        # Reshape for scikit-learn
        X = np.array(dates).reshape(-1, 1)
        y = np.array(price_values)
        
        # Create polynomial features (for non-linear trends)
        poly = PolynomialFeatures(degree=2, include_bias=False)
        X_poly = poly.fit_transform(X)
        
        # Train model
        model = LinearRegression()
        model.fit(X_poly, y)
        
        # Predict for next 30 days
        future_dates = list(range(dates[-1] + 1, dates[-1] + 31))
        future_X = np.array(future_dates).reshape(-1, 1)
        future_X_poly = poly.transform(future_X)
        
        predictions = model.predict(future_X_poly)
        
        # Ensure predictions don't go negative
        predictions = np.maximum(predictions, 0)
        
        # Format prediction data
        prediction_data = []
        base_date = prices.first().timestamp
        
        for i, days in enumerate(future_dates):
            pred_date = base_date + timedelta(days=days)
            pred_price = predictions[i]
            
            prediction_data.append({
                'date': pred_date.strftime('%Y-%m-%d'),
                'predicted_price': float(pred_price)
            })
            
            # Save prediction to database (weekly intervals)
            if i % 7 == 0:
                PricePrediction.objects.update_or_create(
                    product=product,
                    prediction_date=pred_date.date(),
                    defaults={
                        'predicted_price': pred_price,
                        'confidence': 0.8,  # Simplified confidence measure
                        'model_used': 'PolynomialRegression',
                        'features': {'days_since_start': days}
                    }
                )
        
        # Calculate predicted change
        if prediction_data:
            current_price = float(product.current_price)
            final_predicted_price = prediction_data[-1]['predicted_price']
            price_change = final_predicted_price - current_price
            price_change_pct = (price_change / current_price * 100) if current_price > 0 else 0
            
            prediction_summary = {
                'direction': 'up' if price_change > 0 else 'down' if price_change < 0 else 'stable',
                'change_amount': float(price_change),
                'change_percent': float(price_change_pct),
                'confidence': 0.8  # Simplified confidence
            }
        else:
            prediction_summary = None
        
        return Response({
            'product_name': product.name,
            'current_price': float(product.current_price),
            'currency': product.currency,
            'predictions': prediction_data,
            'summary': prediction_summary
        })
