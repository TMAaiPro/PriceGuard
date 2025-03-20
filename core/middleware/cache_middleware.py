import hashlib
import logging
import json
import re
from django.conf import settings
from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

class APICacheMiddleware(MiddlewareMixin):
    """
    Middleware to cache API responses using Redis.
    
    This middleware will cache GET requests to API endpoints
    and serve responses from cache when available.
    """
    
    # Cache timeout in seconds, default to 5 minutes
    CACHE_TIMEOUT = getattr(settings, 'API_CACHE_TIMEOUT', 300)
    
    # Which URL patterns to cache
    CACHE_URL_PATTERNS = [
        r'^/api/products/$',
        r'^/api/products/[\w-]+/$',
        r'^/api/categories/$',
        r'^/api/categories/[\w-]+/$',
        r'^/api/retailers/$',
        r'^/api/brands/$',
        r'^/api/analytics/insights/price_trends/$',
        r'^/api/analytics/insights/market_overview/$',
        r'^/api/analytics/insights/volatility_analysis/$',
    ]
    
    # Which URL patterns to never cache
    NEVER_CACHE_URL_PATTERNS = [
        r'^/api/token/',
        r'^/api/users/',
        r'^/admin/',
    ]
    
    def process_request(self, request):
        """Process the request and return cached response if available"""
        # Only cache GET requests
        if request.method != 'GET':
            return None
            
        # Check if URL should be cached
        path = request.path_info
        if not self._should_cache_url(path):
            return None
            
        # Generate cache key
        cache_key = self._get_cache_key(request)
        
        # Try to get cached response
        cached_response = cache.get(cache_key)
        if cached_response:
            logger.debug(f"Cache hit for {path}")
            return cached_response
            
        return None
    
    def process_response(self, request, response):
        """Process the response and cache it if needed"""
        # Only cache GET requests with 200 status code
        if request.method != 'GET' or response.status_code != 200:
            return response
            
        # Check if URL should be cached
        path = request.path_info
        if not self._should_cache_url(path):
            return response
            
        # Generate cache key
        cache_key = self._get_cache_key(request)
        
        # Cache the response
        logger.debug(f"Caching response for {path}")
        cache.set(cache_key, response, self.CACHE_TIMEOUT)
        
        # Add cache header for debugging
        response['X-API-Cache'] = 'miss'
        
        return response
    
    def _should_cache_url(self, path):
        """Check if URL should be cached"""
        # Check if URL is in never-cache patterns
        for pattern in self.NEVER_CACHE_URL_PATTERNS:
            if re.match(pattern, path):
                return False
        
        # Check if URL is in cache patterns
        for pattern in self.CACHE_URL_PATTERNS:
            if re.match(pattern, path):
                return True
                
        return False
    
    def _get_cache_key(self, request):
        """Generate a cache key based on the request"""
        # Include path and query parameters in the key
        key_parts = [
            request.path_info,
            request.META.get('QUERY_STRING', ''),
        ]
        
        # For authenticated requests, include user ID in the key
        if hasattr(request, 'user') and request.user.is_authenticated:
            key_parts.append(str(request.user.id))
        
        # Join parts and create hash
        key_string = ':'.join(key_parts)
        return f"api:cache:{hashlib.md5(key_string.encode()).hexdigest()}"


class UserBasedCacheMiddleware(MiddlewareMixin):
    """
    Middleware to invalidate user-specific cache entries when user data changes.
    """
    
    def process_request(self, request):
        """Check if we need to invalidate cache for this user"""
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None
            
        # Check cached last modification time
        user_id = str(request.user.id)
        last_modified_key = f"user:{user_id}:last_modified"
        last_modified_cache = cache.get(last_modified_key)
        
        # Get current last modification time
        current_last_modified = request.user.updated_at.timestamp()
        
        # If user data has been modified, invalidate cache
        if last_modified_cache is None or current_last_modified > last_modified_cache:
            logger.debug(f"Invalidating cache for user {user_id}")
            
            # Update last modified time
            cache.set(last_modified_key, current_last_modified, 86400)  # 24 hours
            
            # Delete relevant cache keys
            user_key_pattern = f"api:cache:*:user:{user_id}:*"
            self._delete_pattern(user_key_pattern)
            
        return None
    
    def _delete_pattern(self, pattern):
        """Delete cache keys matching a pattern"""
        # This is a simplified version - for production, use Redis SCAN + DEL
        # or a library like django-redis-cache with wildcards support
        keys = cache.keys(pattern)
        if keys:
            cache.delete_many(keys)
