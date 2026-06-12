from django.urls import path

from .views import BusinessLeadView

urlpatterns = [
    path("lead/", BusinessLeadView.as_view(), name="lead"),
]
