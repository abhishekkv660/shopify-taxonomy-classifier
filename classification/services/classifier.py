import logging
from django.db import transaction
from classification.models import Classification, ClassificationAttribute, AlternativeCategory
from taxonomy.models import TaxonomyCategory, TaxonomyAttribute
from classification.services.candidate_retrieval import CategoryCandidateRetriever
from classification.services.llm_classifier import LLMTaxonomyClassifier

logger = logging.getLogger(__name__)

class ProductClassifier:
    """
    Main orchestration service for product classification.
    Bridges candidate retrieval and structured classification models.
    """
    def __init__(self):
        self.retriever = CategoryCandidateRetriever()
        self.llm_classifier = LLMTaxonomyClassifier()

    def classify(self, product):
        """
        Classify a single product and save the result to the database.
        """
        try:
            # 1. Retrieve candidates via semantic similarity
            candidates = self.retriever.retrieve_candidates(product, top_k=10)
            if not candidates:
                return self._mark_failed(product, "No candidate categories found.")

            # 2. Process candidates through the classification model
            result = self.llm_classifier.classify(product, candidates)
            
            if "error" in result:
                return self._mark_failed(product, result["error"])

            # 3. Save to database
            return self._save_classification(product, result)

        except Exception as e:
            logger.exception(f"Classification failed for product {product.id}: {e}")
            return self._mark_failed(product, str(e))

    @transaction.atomic
    def _save_classification(self, product, result):
        primary_path = result.get("primary_category_path")
        confidence = result.get("confidence_score", 0)
        
        # Determine if manual review is needed
        requires_manual_review = confidence < 70 or not primary_path
        
        # Find the category object
        category = None
        if primary_path:
            category = TaxonomyCategory.objects.filter(full_path=primary_path).first()
            if not category:
                requires_manual_review = True

        # Create or update Classification record
        classification, _ = Classification.objects.update_or_create(
            product=product,
            defaults={
                "predicted_category": category,
                "confidence": min(confidence / 100.0, 1.0) if confidence else None, # model uses 0.0 to 1.0
                "status": Classification.Status.COMPLETED if category else Classification.Status.FAILED,
                "requires_manual_review": requires_manual_review,
                "failure_reason": None if category else "Primary category not matched.",
            }
        )

        # Clear old attributes and alternatives if this is a re-classification
        classification.attributes.all().delete()
        classification.alternative_categories.all().delete()

        # Save extracted attributes
        extracted_attributes = result.get("extracted_attributes", {})
        if category and extracted_attributes:
            for attr_name, attr_value in extracted_attributes.items():
                # Find matching taxonomy attribute loosely (or exactly)
                tax_attr = TaxonomyAttribute.objects.filter(name__iexact=attr_name).first()
                if tax_attr:
                    ClassificationAttribute.objects.create(
                        classification=classification,
                        attribute=tax_attr,
                        value=attr_value,
                        confidence=0.9, # Assuming high confidence if LLM extracted it
                    )
                else:
                    ClassificationAttribute.objects.create(
                        classification=classification,
                        attribute=None, # Extracted something not strictly in taxonomy
                        value=f"{attr_name}: {attr_value}",
                        confidence=0.8,
                    )

        # Save alternatives
        alternatives = result.get("alternative_categories", [])
        if alternatives:
            rank = 1
            for alt_path in alternatives:
                if alt_path == primary_path:
                    continue
                alt_cat = TaxonomyCategory.objects.filter(full_path=alt_path).first()
                if alt_cat:
                    AlternativeCategory.objects.create(
                        classification=classification,
                        category=alt_cat,
                        confidence=0.5, # Dummy value for alternatives
                        rank=rank
                    )
                    rank += 1
                    
        return classification

    def _mark_failed(self, product, reason):
        classification, _ = Classification.objects.update_or_create(
            product=product,
            defaults={
                "status": Classification.Status.FAILED,
                "requires_manual_review": True,
                "failure_reason": reason,
            }
        )
        return classification
