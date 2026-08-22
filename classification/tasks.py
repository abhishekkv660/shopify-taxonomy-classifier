from celery import shared_task
from django.db import transaction
from products.models import Product
from classification.models import Classification
from classification.services.classifier import ProductClassifier
import time
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=10)
def process_unclassified_products_batch(self, product_ids):
    """
    Background task to process a specific batch of products by ID.
    """
    # Fetch products by the provided IDs
    unclassified_products = Product.objects.filter(id__in=product_ids, classification__isnull=True)
    
    if not unclassified_products.exists():
        logger.info("No unclassified products found in this batch.")
        return "No unclassified products."

    classifier = ProductClassifier()
    success_count = 0
    
    for product in unclassified_products:
        logger.info(f"Classifying product: {product.name}")
        
        classification = classifier.classify(product)
        
        if classification.status == Classification.Status.FAILED:
            # Check if it was a rate limit error (429) to trigger Celery retry
            if classification.failure_reason and "429" in classification.failure_reason:
                logger.warning(f"Rate limit hit on {product.id}. Deleting failed attempt and retrying task.")
                # We delete the failed classification so it can be retried properly
                classification.delete()
                # Exponential backoff retry: 10, 20, 40, 80 seconds...
                countdown = 10 * (2 ** self.request.retries)
                raise self.retry(countdown=countdown)
        else:
            success_count += 1
            
        # Add a sleep to respect API limits (e.g. 1 sec between calls = 60 requests/min max)
        time.sleep(1.0)
        
    return f"Processed {len(unclassified_products)} products. {success_count} successful."
