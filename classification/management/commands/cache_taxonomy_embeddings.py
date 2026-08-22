import os
import pickle
import numpy as np
from django.core.management.base import BaseCommand
from django.conf import settings
from sentence_transformers import SentenceTransformer
from taxonomy.models import TaxonomyCategory


class Command(BaseCommand):
    help = "Precompute and cache semantic embeddings for Shopify Taxonomy categories."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Loading SentenceTransformer model (all-MiniLM-L6-v2)..."))
        # We use a lightweight, fast, free semantic embedding model.
        model = SentenceTransformer("all-MiniLM-L6-v2")

        self.stdout.write(self.style.NOTICE("Fetching all categories from the database..."))
        # Get all categories. We can embed the full_path.
        categories = TaxonomyCategory.objects.all().order_by("id")
        
        if not categories.exists():
            self.stdout.write(self.style.ERROR("No taxonomy categories found. Please run import_shopify_taxonomy first."))
            return

        category_data = []
        texts_to_embed = []

        for category in categories:
            # We embed the full path to give the model full semantic context
            # e.g., "Animals & Pet Supplies > Pet Supplies > Dog Beds"
            texts_to_embed.append(category.full_path)
            category_data.append({
                "id": category.id,
                "shopify_id": category.shopify_id,
                "full_path": category.full_path,
                "is_leaf": category.is_leaf
            })

        self.stdout.write(self.style.NOTICE(f"Generating embeddings for {len(texts_to_embed)} categories. This may take a moment..."))
        
        # Compute embeddings in batches to save memory
        embeddings = model.encode(texts_to_embed, batch_size=256, show_progress_bar=True, convert_to_numpy=True)
        
        data_dir = os.path.join(settings.BASE_DIR, "data")
        os.makedirs(data_dir, exist_ok=True)
        cache_path = os.path.join(data_dir, "taxonomy_embeddings.pkl")

        self.stdout.write(self.style.NOTICE(f"Saving embeddings to {cache_path}..."))
        
        with open(cache_path, "wb") as f:
            pickle.dump({
                "categories": category_data,
                "embeddings": embeddings
            }, f)

        self.stdout.write(self.style.SUCCESS(f"Successfully cached embeddings for {len(categories)} categories."))
