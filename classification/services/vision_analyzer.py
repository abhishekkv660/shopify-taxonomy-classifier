import os
import requests
import base64
import logging

logger = logging.getLogger(__name__)

MODEL_NAME = "qwen/qwen3.6-27b"

class VisionAnalyzer:
    def __init__(self):
        self.api_key = os.environ.get("GROQ_API_KEY")

    def analyze_image(self, image_url: str) -> str:
        """
        Downloads an image and asks Gemini to describe it via raw HTTP request.
        """
        if not self.api_key:
            logger.warning("GROQ_API_KEY is not set. Skipping vision analysis.")
            return None

        if not image_url or "http" not in image_url:
            return None

        try:
            img_response = requests.get(image_url, timeout=5)
            img_response.raise_for_status()
            
            mime_type = img_response.headers.get('Content-Type', 'image/jpeg')
            base64_img = base64.b64encode(img_response.content).decode('utf-8')
            
            url = "https://api.groq.com/openai/v1/chat/completions"
            
            prompt = (
                "You are an e-commerce assistant. Analyze this product image. "
                "Describe the object briefly. Then, list any visible attributes "
                "like color, material, pattern, shape, or style. "
                "Keep the output extremely concise."
            )
            
            payload = {
                "model": MODEL_NAME,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_img}"
                                }
                            }
                        ]
                    }
                ],
                "temperature": 0.1
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            api_response = requests.post(url, json=payload, headers=headers, timeout=10)
            api_response.raise_for_status()
            
            data = api_response.json()
            text = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            return text.strip() if text else None
            
        except Exception as e:
            logger.error(f"Vision analysis failed for {image_url}: {str(e)}")
            return None
