from django.core.management.base import BaseCommand
from products.models import Product
from classification.tasks import process_unclassified_products_batch

class Command(BaseCommand):
    help = 'Triggers Celery batch tasks to process unclassified products'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Number of products to process in each Celery task batch',
        )
        parser.add_argument(
            '--num-batches',
            type=int,
            default=1,
            help='Number of concurrent Celery batches to dispatch',
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        num_batches = options['num_batches']

        # Check total unclassified
        total_unclassified = Product.objects.filter(classification__isnull=True).count()
        self.stdout.write(self.style.WARNING(f"Found {total_unclassified} unclassified products in the database."))

        if total_unclassified == 0:
            self.stdout.write(self.style.SUCCESS("All products have been classified!"))
            return

        products_to_process = list(Product.objects.filter(classification__isnull=True).values_list('id', flat=True)[:batch_size * num_batches])
        
        # Split into chunks of `batch_size`
        chunks = [products_to_process[i:i + batch_size] for i in range(0, len(products_to_process), batch_size)]
        
        for i, chunk in enumerate(chunks):
            self.stdout.write(f"Dispatching batch {i+1}/{len(chunks)} ({len(chunk)} products)...")
            process_unclassified_products_batch.delay(product_ids=chunk)
        
        self.stdout.write(self.style.SUCCESS(f"Successfully dispatched {len(chunks)} Celery task(s)! Monitor with 'celery -A config worker -l info --pool=solo'"))
