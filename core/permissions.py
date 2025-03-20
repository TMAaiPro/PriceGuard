from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object or admins to edit it.
    """
    
    def has_object_permission(self, request, view, obj):
        # Admin users can do anything
        if request.user.is_staff:
            return True
            
        # Check if the object has a user field or a created_by field,
        # or other relevant ownership field
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        elif hasattr(obj, 'owner'):
            return obj.owner == request.user
        
        # If we can't determine ownership, deny permission
        return False


class ReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow read-only operations.
    """
    
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS


class IsPremiumUser(permissions.BasePermission):
    """
    Custom permission to only allow premium users to access certain views.
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_premium_active()


class HasMinimumProducts(permissions.BasePermission):
    """
    Custom permission to limit the number of products regular users can track.
    Premium users can track unlimited products.
    """
    max_products_free = 5
    
    def has_permission(self, request, view):
        # Only apply to create operations
        if view.action != 'create' and view.action != 'track_product':
            return True
            
        # Premium users can track unlimited products
        if request.user.is_premium_active():
            return True
            
        # Count user's tracked products
        from products.models import UserProduct
        tracked_count = UserProduct.objects.filter(user=request.user).count()
        
        # Check if limit is reached
        return tracked_count < self.max_products_free
