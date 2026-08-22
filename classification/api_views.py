from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.response import Response
from django.core.management import call_command
import threading
from classification.models import Classification
from classification.serializers import ClassificationSerializer, ClassificationUpdateSerializer

from dashboard.models import ProcessingJob

import threading
import tempfile
import os
from django.core.management import call_command
from rest_framework.parsers import MultiPartParser, FormParser

class UploadProductsAPIView(APIView):
    """Handles Excel file upload and runs import in background"""
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request, *args, **kwargs):
        if 'file' not in request.FILES:
            return Response({"error": "No file provided"}, status=400)
            
        uploaded_file = request.FILES['file']
        fd, temp_path = tempfile.mkstemp(suffix='.xlsx')
        with os.fdopen(fd, 'wb') as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)
                
        def run_import():
            import logging
            logger = logging.getLogger(__name__)
            try:
                call_command('import_products', temp_path)
            except Exception as e:
                logger.error(f"Background import failed: {e}")
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                
        threading.Thread(target=run_import).start()
        return Response({"status": "Import started in the background. Please wait a moment."})

class JobStatusView(APIView):
    """Returns the status of the most recent batch processing job."""
    def get(self, request, *args, **kwargs):
        latest_job = ProcessingJob.objects.order_by('-start_time').first()
        if not latest_job:
            return Response({"active": False})
        
        return Response({
            "active": latest_job.status in ['PENDING', 'PROCESSING'],
            "id": latest_job.id,
            "status": latest_job.status,
            "completed": latest_job.completed,
            "failed": latest_job.failed,
            "total_products": latest_job.total_products
        })

from dashboard.models import ProcessingJob
from products.models import Product
from classification.tasks import process_unclassified_products_batch

class TriggerBatchProcessingView(APIView):
    """Triggers the Celery batch processing directly"""
    def post(self, request, *args, **kwargs):
        batch_size_param = request.data.get('batch_size', '10')
        
        if str(batch_size_param).lower() == 'all':
            unclassified = Product.objects.filter(classification__isnull=True)
        else:
            try:
                batch_size = int(batch_size_param)
                unclassified = Product.objects.filter(classification__isnull=True)[:batch_size]
            except ValueError:
                unclassified = Product.objects.filter(classification__isnull=True)[:10]
                
        product_ids = list(unclassified.values_list('id', flat=True))
        
        if not product_ids:
            return Response({"status": "No products to process."})
            
        job = ProcessingJob.objects.create(
            total_products=len(product_ids),
            status='PROCESSING'
        )
        
        process_unclassified_products_batch.delay(product_ids, job.id)
        
        return Response({
            "status": "Batch processing started",
            "job_id": job.id
        })

from rest_framework.pagination import PageNumberPagination

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100

class ClassificationListView(generics.ListAPIView):
    """
    Returns a list of all classifications.
    Can be filtered by status or manual review flag.
    """
    serializer_class = ClassificationSerializer
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        queryset = Classification.objects.all().order_by('-created_at')
        manual_review = self.request.query_params.get('manual_review')
        if manual_review == 'true':
            queryset = queryset.filter(requires_manual_review=True)
            
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
            
        return queryset

class ClassificationUpdateView(generics.RetrieveUpdateAPIView):
    """
    Allows a human reviewer to retrieve a single classification or update and approve it.
    """
    queryset = Classification.objects.all()
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ClassificationUpdateSerializer
        return ClassificationSerializer
