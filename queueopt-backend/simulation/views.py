import uuid
from datetime import datetime
from django.shortcuts import get_object_or_404
from django.utils.timezone import now

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated, AllowAny

from simulation.models import SimulationResult, Restaurant
from simulation.serializers import (
    SimulationRunRequestSerializer,
    SimulationRunResponseSerializer,
    SimulationResultListSerializer,
    SimulationResultDetailSerializer,
    RestaurantSerializer,
)
from simulation.services.simulation_engine import run_simulation
from simulation.models import Restaurant



class HealthCheckView(APIView):
    def get(self, request):
        return Response(
            {
                "status": "ok",
                "version": "2.0.0",
                "service": "Queue Optimization API",
                "timestamp": datetime.now().isoformat() + "Z",
            }
        )



class RunSimulationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SimulationRunRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Extract restaurant_id and validate ownership
        restaurant_id = data.pop("restaurant_id")
        restaurant = get_object_or_404(
            Restaurant,
            id=restaurant_id,
            owner=request.user,
        )

        config = data  # remaining fields

        simulation_id = f"sim_{uuid.uuid4().hex[:12]}"

        results, metadata = run_simulation(config)

        sim_result = SimulationResult.objects.create(
            simulation_id=simulation_id,
            restaurant=restaurant,
            config=config,
            results=results,
            execution_time_ms=metadata["execution_time_ms"],
            status="completed",
        )

        response_data = {
            "success": True,
            "simulation_id": simulation_id,
            "config": config,
            "results": results,
            "metadata": metadata,
            "message": "Simulation completed successfully.",
        }

        out = SimulationRunResponseSerializer(response_data).data
        return Response(out, status=status.HTTP_200_OK)


class RunGuestSimulationView(APIView):
    """
    Guest simulation endpoint - runs simulation without authentication
    Results are NOT saved to database
    """
    permission_classes = [AllowAny]

    def post(self, request):
        # Create a serializer without restaurant_id requirement
        from simulation.serializers import SimulationRunRequestSerializer
        
        # Make a copy of the data and remove restaurant_id if present
        data = request.data.copy()
        data.pop("restaurant_id", None)
        
        # Create a custom serializer for guest mode (without restaurant_id)
        from rest_framework import serializers
        from simulation.serializers import ServiceTimeParamsSerializer
        
        class GuestSimulationSerializer(serializers.Serializer):
            num_tables = serializers.IntegerField(min_value=10, max_value=100)
            num_servers = serializers.IntegerField(min_value=2, max_value=20)
            arrival_rate = serializers.FloatField(min_value=5, max_value=100)
            duration = serializers.IntegerField(min_value=60, max_value=1440, default=480, required=False)
            party_size_distribution = serializers.DictField(
                child=serializers.FloatField(min_value=0.0, max_value=1.0),
                required=False
            )
            service_time_params = ServiceTimeParamsSerializer(required=False)
            reneg_threshold = serializers.IntegerField(min_value=10, max_value=60, default=30, required=False)
            warmup_period = serializers.IntegerField(min_value=0, max_value=120, default=60, required=False)
            queue_strategy = serializers.ChoiceField(
                choices=("fcfs", "priority_large", "priority_small", "dynamic"),
                default="fcfs",
                required=False
            )
            
            def validate_party_size_distribution(self, value: dict) -> dict:
                if not value:
                    return value
                total = sum(value.values())
                if abs(total - 1.0) > 0.01:
                    raise serializers.ValidationError(
                        f"Party size distribution must sum to 1.0 (±0.01), got {total:.3f}"
                    )
                return value
        
        serializer = GuestSimulationSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        config = serializer.validated_data

        simulation_id = f"guest_{uuid.uuid4().hex[:12]}"

        # Run simulation without saving to database
        results, metadata = run_simulation(config)

        response_data = {
            "success": True,
            "simulation_id": simulation_id,
            "config": config,
            "results": results,
            "metadata": metadata,
            "message": "Guest simulation completed successfully. Login to save results.",
            "guest_mode": True,
        }

        return Response(response_data, status=status.HTTP_200_OK)


class SimulationListView(generics.ListAPIView):
    serializer_class = SimulationResultListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SimulationResult.objects.filter(
            restaurant__owner=self.request.user
        ).order_by("-created_at")

class SimulationDetailView(generics.RetrieveAPIView):
    lookup_field = "simulation_id"
    serializer_class = SimulationResultDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SimulationResult.objects.filter(
            restaurant__owner=self.request.user
        )

class SimulationDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, simulation_id):
        try:
            obj = SimulationResult.objects.get(
                simulation_id=simulation_id,
                restaurant__owner=request.user,
            )
        except SimulationResult.DoesNotExist:
            return Response(
                {"detail": "Simulation not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        obj.delete()
        return Response(
            {"success": True, "message": "Simulation deleted successfully."},
            status=status.HTTP_200_OK,
        )



class RestaurantListCreateView(generics.ListCreateAPIView):
    """
    GET /api/restaurants/  -> list current user's restaurants
    POST /api/restaurants/ -> create a restaurant owned by current user
    """
    serializer_class = RestaurantSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Restaurant.objects.filter(owner=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
