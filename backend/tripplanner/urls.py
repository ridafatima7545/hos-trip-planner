from django.urls import path

from trips.views import PlanTripView

urlpatterns = [
    path("api/plan-trip/", PlanTripView.as_view(), name="plan-trip"),
]
