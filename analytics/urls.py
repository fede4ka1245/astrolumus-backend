from django.urls import path

from . import views

app_name = "analytics"

urlpatterns = [
    path("", views.pnl_dashboard, name="pnl_dashboard"),
    path("dashboards/", views.dashboard_list, name="dashboard_list"),
    path("dashboards/<int:dashboard_id>/", views.dashboard_embed, name="dashboard_embed"),
]
