from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from simulation.views import (
    HealthCheckView,
    RunSimulationView,
    RunGuestSimulationView,
    SimulationListView,
    SimulationDetailView,
    SimulationDeleteView,
    RestaurantListCreateView
)

from simulation.auth_views import (
    RegisterView,
    CustomTokenObtainPairView,
    MeView,
)


urlpatterns = [
    # Health
    path("health/", HealthCheckView.as_view()),

    # --- AUTH ---
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", CustomTokenObtainPairView.as_view(), name="auth-login"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/me/", MeView.as_view(), name="auth-me"),

    # --- SIMULATIONS ---
    path("health/", HealthCheckView.as_view()),
    path("simulation/run/", RunSimulationView.as_view()),
    path("simulation/run-guest/", RunGuestSimulationView.as_view(), name="simulation-run-guest"),
    path("simulations/", SimulationListView.as_view()),
    path("simulations/<str:simulation_id>/", SimulationDetailView.as_view()),
    path("simulations/<str:simulation_id>/delete/", SimulationDeleteView.as_view()),

    path("restaurants/", RestaurantListCreateView.as_view(), name="restaurant-list-create"),

]




