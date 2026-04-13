from rest_framework import serializers
from simulation.models import Restaurant,SimulationConfig,SimulationResult,Experiment,Recommendation



class ServiceTimeParamsSerializer(serializers.Serializer):
    """
    Mirrors the service_time_params object from the spec:
    {
        "mean_by_party_size": {
            "1-2": 45,
            "3-4": 60,
            "5-6": 75,
            "7+": 90
        },
        "std_dev": 10,
        "distribution_type": "normal"
    }
    """

    mean_by_party_size = serializers.DictField(
        child=serializers.FloatField(min_value=20, max_value=240),
        required=False,
        help_text="Mean service times by party size bucket, keys like '1-2', '3-4', '5-6', '7+'.",
    )
    std_dev = serializers.FloatField(
        min_value=5,
        max_value=50,
        default=10,
        required=False,
    )
    distribution_type = serializers.ChoiceField(
        choices=("normal", "exponential", "triangular"),
        default="normal",
        required=False,
    )


class SimulationRunRequestSerializer(serializers.Serializer):
    """
    Request body for POST /api/simulation/run
    (adapted from SimulationRequest in the PDF).
    """

    # NEW:
    restaurant_id = serializers.IntegerField(
        help_text="ID of the restaurant this simulation belongs to.",
    )


    num_tables = serializers.IntegerField(
        min_value=1,
        max_value=100,
        help_text="Number of tables in restaurant.",
    )
    num_servers = serializers.IntegerField(
        min_value=2,
        max_value=20,
        help_text="Number of serving staff.",
    )
    arrival_rate = serializers.FloatField(
        min_value=5,
        max_value=100,
        help_text="Average customers per hour.",
    )
    duration = serializers.IntegerField(
        min_value=60,
        max_value=1440,
        default=480,
        required=False,
        help_text="Simulation duration in minutes.",
    )

    # Object like { "1": 0.05, "2": 0.4, ..., "8": 0.02 }
    party_size_distribution = serializers.DictField(
        child=serializers.FloatField(min_value=0.0, max_value=1.0),
        required=False,
        help_text="Probability distribution for party sizes (keys '1'..'8', must sum ≈ 1.0).",
    )

    service_time_params = ServiceTimeParamsSerializer(
        required=False,
    )

    reneg_threshold = serializers.IntegerField(
        min_value=10,
        max_value=60,
        default=30,
        required=False,
        help_text="Maximum wait time before customer leaves (minutes).",
    )
    warmup_period = serializers.IntegerField(
        min_value=0,
        max_value=120,
        default=60,
        required=False,
        help_text="Initial warmup period to discard (minutes).",
    )
    queue_strategy = serializers.ChoiceField(
        choices=("fcfs", "priority_large", "priority_small", "dynamic"),
        default="fcfs",
        required=False,
    )

    def validate_party_size_distribution(self, value: dict) -> dict:
        """
        Enforce that probs sum to ~1.0 like the Pydantic validator in the spec.
        """
        if not value:
            return value

        total = sum(value.values())
        if abs(total - 1.0) > 0.01:
            raise serializers.ValidationError(
                f"Party size distribution must sum to 1.0 (±0.01), got {total:.3f}"
            )
        return value


class SimulationRunMetadataSerializer(serializers.Serializer):
    execution_time_ms = serializers.FloatField()
    simulation_start_time = serializers.DateTimeField()
    simulation_end_time = serializers.DateTimeField()
    random_seed = serializers.IntegerField(required=False, allow_null=True)
    version = serializers.CharField()


class SimulationRunResponseSerializer(serializers.Serializer):
    """
    Shape of the successful response for /api/simulation/run.
    You can use this in views for explicit response_schema if you want.
    """

    success = serializers.BooleanField()
    simulation_id = serializers.CharField()
    config = serializers.JSONField()
    results = serializers.JSONField()
    metadata = SimulationRunMetadataSerializer()
    message = serializers.CharField()


# -------------------------------------------------------------------
# 2. Model serializers
# -------------------------------------------------------------------


class RestaurantSerializer(serializers.ModelSerializer):
    # owner_id is read-only - set automatically by the view based on authenticated user
    owner_id = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Restaurant
        fields = [
            "id",
            "name",
            "location",
            "address",
            "city",
            "country",
            "owner_id",
            "subscription_plan",
            "subscription_status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["owner_id", "subscription_plan", "subscription_status", "created_at", "updated_at"]


class SimulationConfigSerializer(serializers.ModelSerializer):
    """
    Saved configuration presets for a given restaurant.
    """

    class Meta:
        model = SimulationConfig
        fields = [
            "id",
            "restaurant",
            "name",
            "description",
            "config",
            "created_at",
            "updated_at",
        ]


class SimulationResultListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing simulation history (/api/simulations).
    Shows summary + minimal config/results.
    """

    results_summary = serializers.SerializerMethodField()
    restaurant_name = serializers.SerializerMethodField()

    class Meta:
        model = SimulationResult
        fields = [
            "id",
            "simulation_id",
            "restaurant",
            "restaurant_name",
            "config",
            "results_summary",
            "execution_time_ms",
            "status",
            "created_at",
        ]

    def get_results_summary(self, obj):
        """
        Extract the summary fields the spec shows in the /api/simulations list:
        avg_waiting_time, table_utilization, customers_served.
        We assume results JSON structure follows the engine spec.
        """
        results = obj.results or {}
        perf = results.get("performance_metrics", {})
        util = results.get("utilization_metrics", {})

        return {
            "avg_waiting_time": perf.get("avg_waiting_time"),
            "table_utilization": util.get("table_utilization"),
            "customers_served": perf.get("customers_served"),
        }
    
    def get_restaurant_name(self, obj):
        """Return restaurant name for display"""
        return obj.restaurant.name if obj.restaurant else None


class SimulationResultDetailSerializer(serializers.ModelSerializer):
    """
    Full detail view for GET /api/simulations/{simulation_id}
    (includes full results JSON).
    Also supports PATCH for updating status, error_message, etc.
    """
    
    restaurant_name = serializers.SerializerMethodField()

    class Meta:
        model = SimulationResult
        fields = [
            "id",
            "simulation_id",
            "restaurant",
            "restaurant_name",
            "config",
            "results",
            "execution_time_ms",
            "status",
            "error_message",
            "created_at",
        ]
        read_only_fields = ["id", "simulation_id", "restaurant", "restaurant_name", "config", "results", "execution_time_ms", "created_at"]
    
    def get_restaurant_name(self, obj):
        """Return restaurant name for display"""
        return obj.restaurant.name if obj.restaurant else None


class ExperimentSerializer(serializers.ModelSerializer):
    """
    Experiments store scenarios and comparison_results as JSON.
    """

    class Meta:
        model = Experiment
        fields = [
            "id",
            "name",
            "description",
            "restaurant",
            "scenarios",
            "comparison_results",
            "created_at",
        ]


class RecommendationSerializer(serializers.ModelSerializer):
    """
    Optimization recommendations generated from a given simulation.
    """

    class Meta:
        model = Recommendation
        fields = [
            "id",
            "simulation",          # FK to SimulationResult
            "restaurant",
            "recommendation_type",
            "priority",
            "current_value",
            "recommended_value",
            "expected_improvements",
            "confidence",
            "reasoning",
            "cost_analysis",
            "status",
            "created_at",
        ]



class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = [
            "id",
            "name",
            "location",
            "address",
            "city",
            "country",
            "subscription_plan",
            "subscription_status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["subscription_plan", "subscription_status", "created_at", "updated_at"]
