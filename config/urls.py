from django.contrib import admin
from django.urls import path, include

from simulation.views import backend_home

urlpatterns = [
    path("", backend_home),
    path("admin/", admin.site.urls),
    path("api/", include("simulation.urls")),
]
