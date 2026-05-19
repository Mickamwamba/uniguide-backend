from django.urls import path
from .views import TelemetryTrackingView, SubmitInquiryView, SubmitReportView, SubmitLeadView, SubmitComparisonRatingView

urlpatterns = [
    path('track/', TelemetryTrackingView.as_view(), name='track-telemetry'),
    path('inquiry/', SubmitInquiryView.as_view(), name='submit-inquiry'),
    path('report/', SubmitReportView.as_view(), name='submit-report'),
    path('capture-lead/', SubmitLeadView.as_view(), name='capture-lead'),
    path('comparison-rating/', SubmitComparisonRatingView.as_view(), name='comparison-rating'),
]
