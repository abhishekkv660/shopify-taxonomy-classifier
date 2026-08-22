from celery import shared_task
from django.db import transaction, models
from products.models import Product
from classification.models import Classification
from dashboard.models import ProcessingJob
from classification.services.candidate_retrieval import CategoryCandidateRetriever
from classification.services.llm_classifier import LLMTaxonomyClassifier
from classification.services.classifier import ProductClassifier
from classification.services.vision_analyzer import VisionAnalyzer
import time
import logging

logger = logging.getLogger(__name__)

# Initialize services (they will be reused by the worker process)
retriever = CategoryCandidateRetriever()
llm_classifier = LLMTaxonomyClassifier()
vision_analyzer = VisionAnalyzer()
orchestrator = ProductClassifier(retriever, llm_classifier)

@shared_task(bind=True, max_retries=10)
def process_unclassified_products_batch(self, product_ids, job_id=None):
    """
    Background task to process a specific batch of products by ID.
    Updates the ProcessingJob if job_id is provided.
    """
    # Fetch products by the provided IDs
    unclassified_products = Product.objects.filter(id__in=product_ids, classification__isnull=True)
    
    if not unclassified_products.exists():
        logger.info("No unclassified products found in this batch.")
        return "No products to process."

    # Fetch the job if provided
    job = None
    if job_id:
        job = ProcessingJob.objects.filter(id=job_id).first()

    successful_count = 0
    failed_count = 0
    
    for product in unclassified_products:
        logger.info(f"Classifying product: {product.name}")
        
        try:
            # 1. Vision Analysis (if image exists)
            visual_context = None
            if hasattr(product, 'image_urls') and product.image_urls and len(product.image_urls) > 0:
                visual_context = vision_analyzer.analyze_image(product.image_urls[0])
            
            # 2. Append vision context to product description temporarily for the classifier
            original_description = product.description
            if visual_context:
                product.description = f"{product.description or ''} [Visual Analysis: {visual_context}]"

            # 3. Classify Product
            result = orchestrator.classify(product)
            
            # Restore original description (though it isn't saved, just to be safe in memory)
            product.description = original_description

            if result:
                successful_count += 1
                if job:
                    # Update job progress in database
                    ProcessingJob.objects.filter(id=job_id).update(completed=models.F('completed') + 1)
                    job.refresh_from_db()
                    if (job.completed + job.failed) >= job.total_products:
                        job.status = 'COMPLETED'
                        job.save()
            else:
                failed_count += 1
                if job:
                    ProcessingJob.objects.filter(id=job_id).update(failed=models.F('failed') + 1)
                    job.refresh_from_db()
                    if (job.completed + job.failed) >= job.total_products:
                        job.status = 'COMPLETED'
                        job.save()

        except Exception as e:
            error_msg = str(e)
            
            # Handle rate limiting from Groq or Gemini
            if '429' in error_msg or 'rate limit' in error_msg.lower():
                logger.warning(f"Rate limit hit on {product.id}. Retrying task.")
                # Exponential backoff retry: 10, 20, 40, 80 seconds...
                countdown = 10 * (2 ** self.request.retries)
                raise self.retry(countdown=countdown, exc=e)
            
            logger.error(f"Error processing product {product.id}: {error_msg}")
            failed_count += 1
            if job:
                ProcessingJob.objects.filter(id=job_id).update(failed=models.F('failed') + 1)
                job.refresh_from_db()
                if (job.completed + job.failed) >= job.total_products:
                    job.status = 'COMPLETED'
                    job.save()
            
        # Add a sleep to respect API limits
        time.sleep(1.0)
        
    return f"Processed {len(unclassified_products)} products. {successful_count} successful, {failed_count} failed."
