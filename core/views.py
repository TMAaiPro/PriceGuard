from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

# Create your views here.
class HealthCheckView(APIView):
    """
    Simple health check endpoint to verify if the API is running.
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, format=None):
        return Response(
            {"status": "healthy"},
            status=status.HTTP_200_OK
        )
