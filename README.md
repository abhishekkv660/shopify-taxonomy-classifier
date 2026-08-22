# AI Taxonomy Classifier

An intelligent, massively scalable background processor that ingests raw product data and categorizes it using the official Shopify Taxonomy. Built with Django, Celery, and Groq (LLaMA3).

## Features
- **Semantic Candidate Retrieval:** Uses `SentenceTransformers` (`all-MiniLM-L6-v2`) to instantly find the top 10 closest Shopify categories for a product.
- **LLM Classification:** Uses the Groq API (LLaMA3) to evaluate candidates, select the exact primary path, assign a confidence score (1-100), extract relevant attributes, and provide alternatives.
- **Multimodal Support:** Integrates Google Gemini API to dynamically analyze product images and extract visual context if text metadata is insufficient.
- **Resumable Batch Processing:** Uses a persistent `ProcessingJob` database model and Celery background workers to process up to 10,000+ products continuously without timeout or memory limits. 
- **Graceful Fallbacks:** Automatically falls back to text-only classification if the Image Vision API hits a rate limit (HTTP 429). Flags low-confidence results for manual review.
- **Modern Dashboard UI:** A beautiful, responsive frontend built with Vanilla JS and CSS for reviewing, editing, and approving AI classifications.

## Architecture

1. **Ingestion Layer:** `/api/upload/` accepts `.xlsx` files and asynchronously parses them into the Django database using Pandas, handling missing data gracefully.
2. **Orchestration Layer:** Celery worker processes products asynchronously in batches.
3. **Retrieval Layer:** The product title and description are vectorized locally and compared against the 5,000+ Shopify categories to find candidates.
4. **Classification Layer:** Groq processes the final prompt.
5. **Presentation Layer:** The REST API serves paginated results to the Vanilla JS dashboard.

## Setup Instructions

### 1. Prerequisites
- Python 3.10+
- Conda (recommended) or virtualenv
- Redis (for Celery message brokering)

### 2. Environment Variables
Create a `.env` file in the root directory:
```env
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key
```

### 3. Installation
```bash
conda create -n shopify python=3.10
conda activate shopify
pip install -r requirements.txt
```

### 4. Database Setup
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py import_shopify_taxonomy data/taxonomy_data
```

### 5. Running the Application
You will need three separate terminal windows:

**Terminal 1 (Redis Server):**
*(Ensure Redis is running on port 6379)*

**Terminal 2 (Celery Worker):**
```bash
celery -A core worker -l info --pool=threads
```

**Terminal 3 (Django Server):**
```bash
python manage.py runserver
```

Navigate to `http://127.0.0.1:8000/dashboard/` to view the UI.
