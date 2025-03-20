from django.db.models.signals import post_save
from django.dispatch import receiver
from products.models import ProductPrice, UserProduct
from .models import PriceInsight, UserAnalytics
from django.db import connection
from datetime import datetime, timedelta
import json

@receiver(post_save, sender=ProductPrice)
def analyze_price_history(sender, instance, created, **kwargs):
    """
    Analyze price data when a new price is saved and generate insights if needed
    """
    if not created:
        return
        
    product = instance.product
    
    # Wait until we have enough price data to analyze (at least 5 data points)
    price_count = ProductPrice.objects.filter(product=product).count()
    if price_count < 5:
        return
        
    # Check if we already analyzed this product recently
    recent_insight = PriceInsight.objects.filter(
        product=product,
        created_at__gte=datetime.now() - timedelta(days=1)  # Only one analysis per day
    ).exists()
    
    if recent_insight:
        return
        
    # Get price trend data
    with connection.cursor() as cursor:
        # Load SQL query
        with open('analytics/sql/price_trends.sql', 'r') as f:
            query = f.read()
            
        # Execute with product ID parameter
        cursor.execute(query, {'product_id': product.id})
        
        # Convert result to dict
        columns = [col[0] for col in cursor.description]
        trend_data = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    # Analyze trends
    if trend_data:
        # Calculate simple trend based on first and last day
        first_day = trend_data[0]
        last_day = trend_data[-1]
        price_change = last_day['closing_price'] - first_day['opening_price']
        
        if price_change < 0:
            trend_type = 'downward'
            message = f"Price is trending downward. It decreased by {abs(price_change):.2f} {product.currency} " \
                    f"({abs(price_change) / first_day['opening_price'] * 100:.1f}%) in the last {len(trend_data)} days."
        elif price_change > 0:
            trend_type = 'upward'
            message = f"Price is trending upward. It increased by {price_change:.2f} {product.currency} " \
                    f"({price_change / first_day['opening_price'] * 100:.1f}%) in the last {len(trend_data)} days."
        else:
            trend_type = 'stable'
            message = f"Price has been stable over the last {len(trend_data)} days."
            
        # Create price trend insight
        PriceInsight.objects.create(
            product=product,
            insight_type='trend',
            content=message,
            data={
                'trend_type': trend_type,
                'days_analyzed': len(trend_data),
                'start_price': float(first_day['opening_price']),
                'end_price': float(last_day['closing_price']),
                'price_change': float(price_change),
                'price_change_pct': float(price_change / first_day['opening_price'] * 100) if first_day['opening_price'] > 0 else 0,
                'trend_data': trend_data
            }
        )
        
    # Get volatility data (for products with at least 30 days of data)
    if price_count >= 30:
        with connection.cursor() as cursor:
            # Load SQL query
            with open('analytics/sql/volatility_analysis.sql', 'r') as f:
                query = f.read()
                
            # Execute with product ID parameter
            cursor.execute(query, {'product_id': product.id})
            
            # Convert result to dict
            columns = [col[0] for col in cursor.description]
            volatility_data = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        if volatility_data:
            volatility = volatility_data[0]
            
            # Interpret volatility
            if volatility['coefficient_of_variation'] < 5:
                volatility_level = 'low'
                message = f"Price volatility is low. The price typically varies by less than 5%."
            elif volatility['coefficient_of_variation'] < 15:
                volatility_level = 'medium'
                message = f"Price volatility is moderate. The price typically varies by " \
                        f"{volatility['coefficient_of_variation']:.1f}%."
            else:
                volatility_level = 'high'
                message = f"Price volatility is high. The price is unstable and varies significantly, " \
                        f"by an average of {volatility['coefficient_of_variation']:.1f}%."
                
            # Create volatility insight
            PriceInsight.objects.create(
                product=product,
                insight_type='volatility',
                content=message,
                data={
                    'volatility_level': volatility_level,
                    'days_analyzed': volatility['days_with_data'],
                    'avg_price': float(volatility['period_avg_price']),
                    'price_stddev': float(volatility['price_stddev']),
                    'coefficient_of_variation': float(volatility['coefficient_of_variation']),
                    'avg_daily_range': float(volatility['avg_daily_range']),
                    'avg_daily_range_pct': float(volatility['avg_daily_range_pct'])
                }
            )
