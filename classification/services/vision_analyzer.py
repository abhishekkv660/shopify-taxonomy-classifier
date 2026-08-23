import os
import requests
import base64
import logging
import time

logger = logging.getLogger(__name__)

# We use gemini-3.7-flash which is the latest supported version
MODEL_NAME = "gemini-3.7-flash"

class VisionAnalyzer:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")

    def analyze_image(self, image_url: str) -> str:
        """
        Downloads an image and asks Gemini to describe it via raw HTTP request.
        """
        # Prevent hitting Gemini free tier rate limits (HTTP 429)
        time.sleep(2)

        if not self.api_key:
            logger.warning("GEMINI_API_KEY is not set. Skipping vision analysis.")
            return None

        if not image_url or "http" not in image_url:
            return None

        try:
            # 1. Download image
            img_response = requests.get(image_url, timeout=5)
            img_response.raise_for_status()
            
            mime_type = img_response.headers.get('Content-Type', 'image/jpeg')
            base64_img = base64.b64encode(img_response.content).decode('utf-8')
            
            # 2. Call Gemini API directly (bypassing broken google.generativeai SDK)
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={self.api_key}"
            
            prompt = (
                "You are an e-commerce assistant. Analyze this product image. "
                "Describe the object briefly. Then, list any visible attributes "
                "like color, material, pattern, shape, or style. "
                "Keep the output extremely concise."
            )
            
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": base64_img
                            }
                        }
                    ]
                }]
            }
            
            headers = {"Content-Type": "application/json"}
            api_response = requests.post(url, json=payload, headers=headers, timeout=10)
            api_response.raise_for_status()
            
            data = api_response.json()
            # Extract text from response
            text = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
            
            return text.strip() if text else None
            
        except Exception as e:
            logger.error(f"Vision analysis failed for {image_url}: {str(e)}")
            return None
