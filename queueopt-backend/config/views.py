from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status


@api_view(['GET'])
def health_check(request):
    """
    Health check endpoint that returns a success response.
    """
    return Response({
        "status": "success",
        "message": "Backend is running successfully",
        "service": "Queue Optimization System for Restaurants"
    }, status=status.HTTP_200_OK)

