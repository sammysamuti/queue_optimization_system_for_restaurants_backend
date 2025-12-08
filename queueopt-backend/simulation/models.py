from django.db import models
from django.conf import settings


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Restaurant(TimeStampedModel):
    """
    Represents a restaurant using the queue optimization system.
    """

    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)

    # We'll assume owner is a Django user (settings.AUTH_USER_MODEL)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_restaurants",
    )

    subscription_plan = models.CharField(
        max_length=50,
        default="basic",
        db_index=True,
    )
    subscription_status = models.CharField(
        max_length=50,
        default="active",
        db_index=True,
    )

    def __str__(self):
        return self.name

    class Meta:
        db_table = "restaurants"
        indexes = [
            models.Index(fields=["owner"], name="idx_owner_id"),
            models.Index(
                fields=["subscription_plan", "subscription_status"],
                name="idx_subscription",
            ),
        ]


class SimulationConfig(TimeStampedModel):
    """
    Saved simulation configuration preset for a given restaurant.
    Mirrors simulation_configs table.
    """

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="simulation_configs",
    )

    name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    # Postgres JSONB underneath when using PostgreSQL
    config = models.JSONField()

    def __str__(self):
        return self.name or f"Config #{self.pk}"

    class Meta:
        db_table = "simulation_configs"
        indexes = [
            models.Index(fields=["restaurant"], name="idx_simcfg_restaurant"),
            models.Index(fields=["created_at"], name="idx_simcfg_created_at"),
        ]

class SimulationResult(TimeStampedModel):
    """
    Stores the results of a single simulation run.
    Mirrors simulation_results table.
    """

    # External ID used in the API response (e.g., "sim_abc123xyz789")
    simulation_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
    )

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="simulation_results",
        null=True, blank=True,
    )

    # Optional link to a saved SimulationConfig
    config_obj = models.ForeignKey(
        SimulationConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="results",
    )

    # Raw config snapshot used for this run (even if config_obj changes later)
    config = models.JSONField()

    # Full results JSON (performance_metrics, queue_metrics, etc.)
    results = models.JSONField()

    execution_time_ms = models.IntegerField(null=True, blank=True)

    status = models.CharField(
        max_length=50,
        default="completed",
        db_index=True,
    )

    error_message = models.TextField(blank=True)

    def __str__(self):
        return self.simulation_id

    class Meta:
        db_table = "simulation_results"
        indexes = [
            models.Index(fields=["restaurant"], name="idx_simres_restaurant"),
            models.Index(fields=["created_at"], name="idx_simres_created_at"),
            models.Index(fields=["status"], name="idx_simres_status"),
        ]

class Experiment(TimeStampedModel):
    """
    Scenario comparison experiments (e.g. baseline vs more tables vs more servers).
    Mirrors experiments table.
    """

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="experiments",
    )

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # List of scenarios to compare (JSONB in Postgres)
    # Each scenario will look like { "name": ..., "description": ..., "config": {...} }
    scenarios = models.JSONField()

    # Aggregated comparison results (e.g., best_waiting_time, best_utilization, etc.)
    comparison_results = models.JSONField(null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "experiments"
        indexes = [
            models.Index(fields=["restaurant"], name="idx_experiment_restaurant"),
        ]

class Recommendation(TimeStampedModel):
    """
    Optimization recommendations derived from simulation results.
    Mirrors recommendations table.
    """

    # Link to simulation via its simulation_id string
    simulation = models.ForeignKey(
        SimulationResult,
        to_field="simulation_id",
        db_column="simulation_id",
        on_delete=models.CASCADE,
        related_name="recommendations",
    )

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="recommendations",
        null=True, blank=True,
    )

    recommendation_type = models.CharField(max_length=100)
    priority = models.CharField(max_length=50, default="medium")

    current_value = models.JSONField(null=True, blank=True)
    recommended_value = models.JSONField(null=True, blank=True)
    expected_improvements = models.JSONField(null=True, blank=True)

    confidence = models.FloatField(null=True, blank=True)
    reasoning = models.TextField(blank=True)
    cost_analysis = models.JSONField(null=True, blank=True)

    status = models.CharField(
        max_length=50,
        default="pending",
        db_index=True,
    )

    def __str__(self):
        return f"{self.recommendation_type} ({self.simulation_id})"

    class Meta:
        db_table = "recommendations"
        indexes = [
            models.Index(fields=["simulation"], name="idx_rec_simulation"),
            models.Index(fields=["restaurant"], name="idx_rec_restaurant"),
            models.Index(fields=["status"], name="idx_rec_status"),
        ]
