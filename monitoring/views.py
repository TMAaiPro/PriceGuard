from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Count, Q

from .models import MonitoringTask, ProductMonitoringConfig, MonitoringResult, MonitoringStats
from .serializers import (
    MonitoringTaskSerializer, MonitoringTaskDetailSerializer,
    ProductMonitoringConfigSerializer, MonitoringResultSerializer,
    MonitoringResultDetailSerializer, MonitoringStatsSerializer
)
from .services import MonitoringScheduler, MonitoringPrioritizer
from .tasks import schedule_monitoring_tasks

class MonitoringTaskViewSet(viewsets.ModelViewSet):
    """API viewset pour les tâches de monitoring"""
    queryset = MonitoringTask.objects.all().order_by('-created_at')
    serializer_class = MonitoringTaskSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'product']
    search_fields = ['product__title', 'error_message']
    ordering_fields = ['created_at', 'scheduled_time', 'priority', 'status']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return MonitoringTaskDetailSerializer
        return MonitoringTaskSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated()]
    
    @action(detail=False, methods=['post'])
    def schedule_product(self, request):
        """Planifie le monitoring immédiat d'un produit spécifique"""
        product_id = request.data.get('product_id')
        priority = request.data.get('priority')
        
        if not product_id:
            return Response({'error': 'product_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        task = MonitoringScheduler.schedule_specific_product(product_id, priority)
        
        if task:
            serializer = self.get_serializer(task)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'])
    def schedule_batch(self, request):
        """Planifie un lot de tâches de monitoring"""
        batch_size = request.data.get('batch_size', 1000)
        
        # Lancer la tâche Celery de planification
        result = schedule_monitoring_tasks.delay(batch_size)
        
        return Response({
            'message': f'Scheduled monitoring batch of up to {batch_size} products',
            'task_id': result.id
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Statistiques sur les tâches de monitoring"""
        total = MonitoringTask.objects.count()
        pending = MonitoringTask.objects.filter(status='pending').count()
        scheduled = MonitoringTask.objects.filter(status='scheduled').count()
        running = MonitoringTask.objects.filter(status='running').count()
        completed = MonitoringTask.objects.filter(status='completed').count()
        failed = MonitoringTask.objects.filter(status='failed').count()
        
        # Tâches par priorité
        high_priority = MonitoringTask.objects.filter(priority__lte=3).count()
        normal_priority = MonitoringTask.objects.filter(priority__gt=3, priority__lte=7).count()
        low_priority = MonitoringTask.objects.filter(priority__gt=7).count()
        
        # Tâches par jour (7 derniers jours)
        seven_days_ago = timezone.now() - timezone.timedelta(days=7)
        tasks_by_day = (
            MonitoringTask.objects
            .filter(created_at__gte=seven_days_ago)
            .extra({'day': "DATE(created_at)"})
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )
        
        return Response({
            'total': total,
            'pending': pending,
            'scheduled': scheduled,
            'running': running,
            'completed': completed,
            'failed': failed,
            'high_priority': high_priority,
            'normal_priority': normal_priority,
            'low_priority': low_priority,
            'tasks_by_day': tasks_by_day
        })


class ProductMonitoringConfigViewSet(viewsets.ModelViewSet):
    """API viewset pour la configuration de monitoring des produits"""
    queryset = ProductMonitoringConfig.objects.all()
    serializer_class = ProductMonitoringConfigSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['active', 'frequency', 'product']
    search_fields = ['product__title']
    ordering_fields = ['priority_score', 'next_scheduled', 'last_monitored']
    
    @action(detail=True, methods=['post'])
    def update_frequency(self, request, pk=None):
        """Met à jour la fréquence de monitoring d'un produit"""
        config = self.get_object()
        
        frequency = request.data.get('frequency')
        custom_hours = request.data.get('custom_frequency_hours')
        
        if not frequency or frequency not in dict(ProductMonitoringConfig.FREQUENCY_CHOICES):
            return Response({'error': 'Valid frequency is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if frequency == 'custom' and not custom_hours:
            return Response({'error': 'custom_frequency_hours is required for custom frequency'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        config.frequency = frequency
        if frequency == 'custom':
            config.custom_frequency_hours = max(1, min(168, int(custom_hours)))
        
        # Recalculer la prochaine vérification
        if config.last_monitored:
            interval_hours = config.get_monitoring_interval()
            config.next_scheduled = config.last_monitored + timezone.timedelta(hours=interval_hours)
        
        config.save()
        
        serializer = self.get_serializer(config)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def update_priority(self, request, pk=None):
        """Met à jour manuellement la priorité d'un produit"""
        config = self.get_object()
        
        boost = request.data.get('manual_priority_boost')
        
        if boost is None:
            return Response({'error': 'manual_priority_boost is required'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        # Limiter entre 0 et 10
        boost = max(0, min(10, float(boost)))
        
        config.manual_priority_boost = boost
        config.save()
        
        # Recalculer le score de priorité
        MonitoringPrioritizer._update_product_priority(config.product)
        
        serializer = self.get_serializer(config)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        """Met à jour en masse les configurations de monitoring"""
        product_ids = request.data.get('product_ids', [])
        update_data = request.data.get('update_data', {})
        
        if not product_ids or not update_data:
            return Response({'error': 'product_ids and update_data are required'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        # Filtrer les champs autorisés pour la mise à jour
        allowed_fields = ['active', 'frequency', 'custom_frequency_hours', 
                         'take_screenshot', 'notify_on_any_change',
                         'price_threshold_percentage', 'price_threshold_absolute']
        
        update_fields = {k: v for k, v in update_data.items() if k in allowed_fields}
        
        if not update_fields:
            return Response({'error': 'No valid fields to update'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        # Effectuer la mise à jour
        updated_count = (
            ProductMonitoringConfig.objects
            .filter(product_id__in=product_ids)
            .update(**update_fields)
        )
        
        return Response({
            'message': f'Updated {updated_count} configurations',
            'updated_count': updated_count
        })


class MonitoringResultViewSet(viewsets.ReadOnlyModelViewSet):
    """API viewset pour les résultats de monitoring (lecture seule)"""
    queryset = MonitoringResult.objects.all().order_by('-monitored_at')
    serializer_class = MonitoringResultSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['product', 'price_changed', 'availability_changed', 'alert_triggered', 'alert_type']
    search_fields = ['product__title', 'alert_message']
    ordering_fields = ['monitored_at', 'current_price', 'price_change_percentage']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return MonitoringResultDetailSerializer
        return MonitoringResultSerializer
    
    @action(detail=False, methods=['get'])
    def product_history(self, request):
        """Historique de monitoring pour un produit spécifique"""
        product_id = request.query_params.get('product_id')
        limit = int(request.query_params.get('limit', 20))
        
        if not product_id:
            return Response({'error': 'product_id is required'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        results = (
            MonitoringResult.objects
            .filter(product_id=product_id)
            .order_by('-monitored_at')[:limit]
        )
        
        serializer = self.get_serializer(results, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recent_alerts(self, request):
        """Récupère les alertes récentes"""
        days = int(request.query_params.get('days', 7))
        limit = int(request.query_params.get('limit', 50))
        
        since_date = timezone.now() - timezone.timedelta(days=days)
        
        alerts = (
            MonitoringResult.objects
            .filter(
                alert_triggered=True,
                monitored_at__gte=since_date
            )
            .select_related('product')
            .order_by('-monitored_at')[:limit]
        )
        
        serializer = self.get_serializer(alerts, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def price_trends(self, request):
        """Récupère les tendances de prix pour un produit"""
        product_id = request.query_params.get('product_id')
        days = int(request.query_params.get('days', 30))
        
        if not product_id:
            return Response({'error': 'product_id is required'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        since_date = timezone.now() - timezone.timedelta(days=days)
        
        results = (
            MonitoringResult.objects
            .filter(
                product_id=product_id,
                monitored_at__gte=since_date
            )
            .order_by('monitored_at')
        )
        
        # Formater les données pour le graphique
        data_points = []
        for result in results:
            data_points.append({
                'date': result.monitored_at.strftime('%Y-%m-%d'),
                'price': float(result.current_price),
                'available': result.currently_available,
                'is_deal': result.is_deal
            })
        
        return Response(data_points)


class MonitoringStatsViewSet(viewsets.ReadOnlyModelViewSet):
    """API viewset pour les statistiques de monitoring (lecture seule)"""
    queryset = MonitoringStats.objects.all().order_by('-date')
    serializer_class = MonitoringStatsSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['date']
    ordering_fields = ['date', 'total_tasks', 'completed_tasks', 'failed_tasks']
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Résumé des statistiques de monitoring"""
        days = int(request.query_params.get('days', 30))
        
        since_date = timezone.now().date() - timezone.timedelta(days=days)
        
        stats = MonitoringStats.objects.filter(date__gte=since_date)
        
        # Agréger les statistiques
        summary = {
            'total_tasks': sum(s.total_tasks for s in stats),
            'completed_tasks': sum(s.completed_tasks for s in stats),
            'failed_tasks': sum(s.failed_tasks for s in stats),
            'price_changes_detected': sum(s.price_changes_detected for s in stats),
            'availability_changes_detected': sum(s.availability_changes_detected for s in stats),
            'alerts_triggered': sum(s.alerts_triggered for s in stats),
            'high_priority_tasks': sum(s.high_priority_tasks for s in stats),
            'normal_priority_tasks': sum(s.normal_priority_tasks for s in stats),
            'low_priority_tasks': sum(s.low_priority_tasks for s in stats),
        }
        
        # Calculer les moyennes
        if stats:
            avg_execution_times = [s.avg_execution_time for s in stats if s.avg_execution_time is not None]
            if avg_execution_times:
                summary['avg_execution_time'] = sum(avg_execution_times) / len(avg_execution_times)
            
            # Trouver les maximums
            max_times = [s.max_execution_time for s in stats if s.max_execution_time is not None]
            if max_times:
                summary['max_execution_time'] = max(max_times)
        
        # Données par jour
        daily_data = []
        for stat in stats.order_by('date'):
            daily_data.append({
                'date': stat.date.strftime('%Y-%m-%d'),
                'total_tasks': stat.total_tasks,
                'completed_tasks': stat.completed_tasks,
                'failed_tasks': stat.failed_tasks,
                'alerts_triggered': stat.alerts_triggered,
            })
        
        summary['daily_data'] = daily_data
        
        return Response(summary)
