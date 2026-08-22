import json
from groq import Groq
from django.conf import settings

class LLMTaxonomyClassifier:
    """
    Classifies products into Shopify taxonomy categories using a configured Groq model.
    Returns structured JSON containing the selected category, attributes, confidence, and alternatives.
    """
    MODEL = "openai/gpt-oss-20b"

    def __init__(self):
        self.client = Groq(
            api_key=settings.GROQ_API_KEY
        )

    def classify(self, product, candidate_categories):
        """
        Evaluates the best category from the candidates, extracts attributes, 
        and assigns a confidence score using the configured model.
        """
        candidate_paths = "\n".join(
            f"- {category.full_path}"
            for category in candidate_categories
        )

        prompt = f"""
You are a product taxonomy classification system for Shopify.

Your task is to classify a product into the most appropriate Shopify taxonomy category from the given candidates.

PRODUCT INFORMATION:
Name: {product.name or "Not provided"}
Product Type: {product.product_type or "Not provided"}
Product Category: {product.product_category or "Not provided"}
Product Subcategory: {product.product_sub_category or "Not provided"}
Brand: {product.brand if hasattr(product, 'brand') else "Not provided"}
Description: {product.description or "Not provided"}

CANDIDATE CATEGORIES:
{candidate_paths}

INSTRUCTIONS:
1. Choose exactly ONE primary_category_path from the CANDIDATE CATEGORIES.
2. Provide a confidence_score between 1 and 100.
3. If confidence_score < 80, provide 1 to 3 alternative_categories from the candidates.
4. Extract key product attributes that fit the selected category (e.g., Color, Material) as key-value pairs in extracted_attributes.

Respond ONLY with valid JSON matching this schema:
{{
  "primary_category_path": "string or null",
  "confidence_score": 85,
  "alternative_categories": ["string", "string"],
  "extracted_attributes": {{"string": "string"}}
}}
"""

        try:
            response = self.client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {
                        "content": "You are a Shopify classification system. Output valid JSON matching the schema strictly.",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.1,
            )

            result_text = response.choices[0].message.content.strip()
            return json.loads(result_text)
            
        except Exception as e:
            return {
                "primary_category_path": None,
                "confidence_score": 0,
                "alternative_categories": [],
                "extracted_attributes": {},
                "error": str(e)
            }
