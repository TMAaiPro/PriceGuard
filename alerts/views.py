from django.db.models import Count
from rest_framework import viewsets, permissions, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend

from .models import Alert, AlertType, AlertConfiguration, AlertAction
from .serializers import (
    AlertSerializer, AlertListSerializer, AlertTypeSerializer,
    AlertConfigurationSerializer, AlertActionSerializer
)


class AlertViewSet(viewsets.ModelViewSet):
    """Viewset for user alerts"""
    serializer_class = AlertSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['alert_type', 'status', 'product']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Return only alerts for the authenticated user"""
        return Alert.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        """Return appropriate serializer class"""
        if self.action == 'list':
            return AlertListSerializer
        return self.serializer_class
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark an alert as read"""
        alert = self.get_object()
        if alert.status == 'new':
            alert.status = 'read'
            alert.save()
            
            # Create an action record
            AlertAction.objects.create(
                alert=alert,
                action='view'
            )
            
        serializer = self.get_serializer(alert)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def dismiss(self, request, pk=None):
        """Dismiss an alert"""
        alert = self.get_object()
        alert.status = 'dismissed'
        alert.save()
        
        # Create an action record
        AlertAction.objects.create(
            alert=alert,
            action='dismiss'
        )
        
        serializer = self.get_serializer(alert)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def action_taken(self, request, pk=None):
        """Record that an action was taken on an alert"""
        alert = self.get_object()
        alert.status = 'actioned'
        alert.save()
        
        # Create an action record
        action_type = request.data.get('action_type', 'click')
        if action_type not in ['click', 'save', 'purchase']:
            action_type = 'click'
            
        AlertAction.objects.create(
            alert=alert,
            action=action_type,
            details=request.data.get('details')
        )
        
        serializer = self.get_serializer(alert)
        return Response(serializer.data)


class AlertTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """Viewset for alert types"""
    queryset = AlertType.objects.filter(is_active=True)
    serializer_class = AlertTypeSerializer
    permission_classes = [permissions.IsAuthenticated]


class AlertConfigurationViewSet(viewsets.ModelViewSet):
    """Viewset for user alert configurations"""
    serializer_class = AlertConfigurationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Return only configurations for the authenticated user"""
        return AlertConfiguration.objects.filter(user=self.request.user)


class AlertSummaryView(APIView):
    """View for getting a summary of user's alerts"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, format=None):
        """Return summary of alerts by status and type"""
        user = request.user
        
        # Count by status
        status_counts = Alert.objects.filter(user=user).values('status').annotate(
            count=Count('id')
        )
        
        # Count by type
        type_counts = Alert.objects.filter(user=user).values(
            'alert_type__id', 'alert_type__name'
        ).annotate(count=Count('id'))
        
        # Get a few recent alerts
        recent_alerts = Alert.objects.filter(user=user).order_by('-created_at')[:5]
        recent_serializer = AlertListSerializer(recent_alerts, many=True)
        
        # Format response
        status_summary = {item['status']: item['count'] for item in status_counts}
        type_summary = {
            item['alert_type__name']: item['count'] for item in type_counts
        }
        
        return Response({
            'total': sum(status_summary.values()),
            'unread': status_summary.get('new', 0),
            'by_status': status_summary,
            'by_type': type_summary,
            'recent': recent_serializer.data
        })


class MarkAllAlertsReadView(APIView):
    """View for marking all alerts as read"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, format=None):
        """Mark all unread alerts as read"""
        user = request.user
        unread_alerts = Alert.objects.filter(user=user, status='new')
        count = unread_alerts.count()
        
        # Update all alerts
        unread_alerts.update(status='read')
        
        # Create action records
        alerts_list = list(unread_alerts)
        actions = [
            AlertAction(alert_id=alert.id, action='view')
            for alert in alerts_list
        ]
        
        if actions:
            AlertAction.objects.bulk_create(actions)
        
        return Response({
            'status': 'success',
            'message': f'Marked {count} alerts as read',
            'count': count
        })
