from django.test import TestCase
from unittest.mock import patch
from products.models import Product
from taxonomy.models import TaxonomyCategory
from classification.models import Classification
from classification.services.classifier import ProductClassifier
from dashboard.models import ProcessingJob
from classification.tasks import process_unclassified_products_batch

class ClassificationTests(TestCase):
    def setUp(self):
        self.category = TaxonomyCategory.objects.create(
            shopify_id="sg-123",
            name="Chairs",
            full_path="Furniture > Chairs",
            level=2
        )
        self.product = Product.objects.create(
            product_number="test-123",
            name="Test Chair",
            description="A nice chair.",
            image_urls=["http://example.com/chair.jpg"]
        )
        self.job = ProcessingJob.objects.create(total_products=1, status='IN_PROGRESS')

    @patch('classification.services.llm_classifier.LLMTaxonomyClassifier.classify')
    @patch('classification.services.candidate_retrieval.CategoryCandidateRetriever.retrieve_candidates')
    @patch('classification.services.vision_analyzer.VisionAnalyzer.analyze_image')
    def test_successful_classification_with_vision(self, mock_vision, mock_retriever, mock_llm):
        """Tests that the full Celery batch pipeline correctly integrates vision, retrieval, and LLM."""
        # Mock vision response
        mock_vision.return_value = "A red wooden chair."
        
        # Mock retriever
        mock_retriever.return_value = [{"id": "sg-123", "name": "Furniture > Chairs", "path": "Furniture > Chairs"}]
        
        # Mock LLM response
        mock_llm.return_value = {
            "primary_category_path": "Furniture > Chairs",
            "confidence_score": 95,
            "requires_manual_review": False,
            "extracted_attributes": {"Color": "Red"}
        }

        # Run Celery Task synchronously
        process_unclassified_products_batch(product_ids=[self.product.id], job_id=self.job.id)
        
        # Verify Classification
        classification = Classification.objects.get(product=self.product)
        self.assertEqual(classification.predicted_category, self.category)
        self.assertEqual(float(classification.confidence), 0.95)
        self.assertEqual(classification.status, Classification.Status.COMPLETED)
        
        # Verify Job tracking updated
        self.job.refresh_from_db()
        self.assertEqual(self.job.completed, 1)
        self.assertEqual(self.job.failed, 0)

    @patch('classification.services.llm_classifier.LLMTaxonomyClassifier.classify')
    def test_api_failure_flags_manual_review(self, mock_llm):
        """Tests that a crashing API safely isolates the failure and flags the product for review."""
        # Mock LLM raising an exception (e.g. 500 Server Error)
        mock_llm.side_effect = Exception("API Timeout")
        
        from classification.services.candidate_retrieval import CategoryCandidateRetriever
        from classification.services.llm_classifier import LLMTaxonomyClassifier
        
        # We don't mock Retriever here, we just want to test Orchestrator exception handling
        retriever_mock = CategoryCandidateRetriever()
        retriever_mock.retrieve_candidates = lambda x, **kwargs: [{"id": "dummy"}]
        orchestrator = ProductClassifier(retriever_mock, LLMTaxonomyClassifier())
        
        # Execute
        classification = orchestrator.classify(self.product)
        
        # Verify defensive failure isolation
        self.assertIsNotNone(classification)
        self.assertEqual(classification.status, Classification.Status.FAILED)
        self.assertTrue(classification.requires_manual_review)
        self.assertEqual(classification.failure_reason, "API Timeout")
