import os
import pickle
import numpy as np
from django.conf import settings
from sentence_transformers import SentenceTransformer
from taxonomy.models import TaxonomyCategory


class CategoryCandidateRetriever:
    """
    Retrieve Shopify taxonomy category candidates using semantic embeddings.
    Replaces the legacy rule-based approach with vector similarities.
    """

    def __init__(self):
        # Load the precomputed embeddings cache
        cache_path = os.path.join(settings.BASE_DIR, "data", "taxonomy_embeddings.pkl")
        if not os.path.exists(cache_path):
            raise FileNotFoundError(f"Embeddings cache not found at {cache_path}. Run 'python manage.py cache_taxonomy_embeddings' first.")
            
        with open(cache_path, "rb") as f:
            cache_data = pickle.load(f)
            
        self.categories_data = cache_data["categories"]
        self.embeddings = cache_data["embeddings"]
        
        # We also need the embedding model to encode incoming products
        # This will be loaded into memory. all-MiniLM-L6-v2 is small and fast.
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def _build_product_text(self, product):
        """
        Combine product fields into a meaningful semantic string.
        """
        parts = []
        if product.name:
            parts.append(product.name)
        if product.description:
            # truncate description to avoid diluting the core identity too much
            desc = product.description[:500] 
            parts.append(desc)
        if product.product_type:
            parts.append(f"Type: {product.product_type}")
        if product.product_sub_category:
            parts.append(f"Subcategory: {product.product_sub_category}")
        
        return " | ".join(parts)

    def retrieve_candidates(self, product, top_k=10):
        """
        Retrieve the top K candidate categories for the given product.
        """
        product_text = self._build_product_text(product)
        if not product_text:
            return []

        # Generate embedding for the product
        product_embedding = self.model.encode(product_text, convert_to_numpy=True)
        
        # Calculate cosine similarity
        # Since embeddings from sentence-transformers are often normalized,
        # dot product is equivalent to cosine similarity, but we'll use actual cosine
        # for safety if not strictly normalized.
        
        norm_product = np.linalg.norm(product_embedding)
        norm_categories = np.linalg.norm(self.embeddings, axis=1)
        
        # Avoid division by zero
        if norm_product == 0:
            return []
            
        # Cosine similarity = (A dot B) / (||A|| ||B||)
        dot_products = np.dot(self.embeddings, product_embedding)
        similarities = dot_products / (norm_categories * norm_product)
        
        # Get top K indices
        # argpartition is faster than argsort for top K
        if len(similarities) > top_k:
            top_indices = np.argpartition(similarities, -top_k)[-top_k:]
            # argpartition doesn't sort the top K, so we sort them
            top_indices = top_indices[np.argsort(similarities[top_indices])[::-1]]
        else:
            top_indices = np.argsort(similarities)[::-1]
            
        # Map indices back to Django ORM objects
        candidate_ids = [self.categories_data[idx]["id"] for idx in top_indices]
        
        from django.db import models
        # Map indices back to Django ORM objects while preserving similarity ranking
        preserved_order = models.Case(
            *[models.When(pk=pk, then=pos) for pos, pk in enumerate(candidate_ids)]
        )
        
        return list(TaxonomyCategory.objects.filter(id__in=candidate_ids).order_by(preserved_order))