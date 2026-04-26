from django.urls import path
from .views import TelemetryTrackingView

urlpatterns = [
    path('track/', TelemetryTrackingView.as_view(), name='track-telemetry'),
]
