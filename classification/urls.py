from django.urls import path
from .api_views import ClassificationListView, ClassificationUpdateView, TriggerBatchProcessingView, JobStatusView, UploadProductsAPIView

urlpatterns = [
    path('api/classifications/', ClassificationListView.as_view(), name='classification-list'),
    path('api/classifications/<int:pk>/', ClassificationUpdateView.as_view(), name='classification-update'),
    path('api/process-batch/', TriggerBatchProcessingView.as_view(), name='api-process-batch'),
    path('api/job-status/', JobStatusView.as_view(), name='api-job-status'),
    path('api/upload/', UploadProductsAPIView.as_view(), name='api-upload'),
]
