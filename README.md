# AI Taxonomy Classifier

## 1. Project Overview
An intelligent, massively scalable background processor that ingests raw product data and categorizes it using the official Shopify Taxonomy. Built with Django, Celery, and Groq (LLaMA3).

## 2. Problem Statement
The goal is to automatically detect the Shopify Product Taxonomy category, category attributes, and attribute values for a catalogue containing 10,000+ products, handling missing descriptions, missing images, and failures gracefully without stopping batch processing.

## 3. Architecture
The application follows a decoupled 3-tier architecture:
1. **Frontend:** Vanilla JS / CSS dashboard.
2. **Web Tier:** Django WSGI server handling HTTP/API requests and MariaDB interactions.
3. **Worker Tier:** Asynchronous Celery workers pulling tasks from Redis, querying a local `SentenceTransformer` vector space, and inferring via Groq/Gemini APIs.

## 4. Technology Stack
- **Backend:** Python, Django, Django REST Framework
- **Database:** MariaDB
- **Background Processing:** Celery, Redis
- **AI/ML:** `sentence-transformers` (Local), Groq (LLaMA3), Google Gemini Pro Vision
- **Deployment:** Docker, Docker Compose

## 5. Features
- **Semantic Candidate Retrieval:** Uses `SentenceTransformers` to instantly find the top 10 closest Shopify categories.
- **LLM Classification & Multimodal Support:** Uses Groq (LLaMA3) for text analysis and Gemini for image analysis.
- **Resumable Batch Processing:** Processes 10,000+ products continuously without timeouts.
- **Graceful Fallbacks:** Falls back to text-only classification on image API rate limits (HTTP 429).
- **Modern Dashboard UI:** For reviewing, editing, and approving AI classifications.

## 6. Project Structure
- `classification/`: Core ML, NLP logic, Celery tasks, and API views.
- `dashboard/`: Vanilla JS and HTML templates for the UI.
- `products/`: Product ingestion and storage logic.
- `taxonomy/`: Shopify taxonomy models and parsing commands.
- `config/`: Django routing and settings.

## 7. Prerequisites
- Docker & Docker Compose (Recommended)
- **OR** Python 3.10+, Redis server, and MariaDB (for bare-metal).

## 8. MariaDB Setup
If not using Docker, ensure MariaDB is running locally. Create a database `taxonomy_db` and user `taxonomy_user` (or update `.env` to match your local credentials).

## 9. Environment Variables
Create a `.env` file in the root directory:
```env
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key
DB_NAME=taxonomy_db
DB_USER=taxonomy_user
DB_PASSWORD=your_password
```

## 10. Installation
**Option A: Docker (Recommended)**
```bash
docker-compose up --build
```
*(This automatically runs migrations and seeds the taxonomy. Skip to step 13).*

**Option B: Bare-Metal**
```bash
conda create -n shopify python=3.10
conda activate shopify
pip install -r requirements.txt
```
*(Note: A convenient `run_local.bat` script is included for Windows users to instantly launch all required servers after completing steps 11 and 12).*

## 11. Database Migration (Bare-Metal)
```bash
python manage.py migrate
```

## 12. Shopify Taxonomy Setup (Bare-Metal)
```bash
python manage.py import_shopify_taxonomy data/taxonomy_data
```

## 13. Product Import
*(Note: Ensure the application and workers from Steps 14 and 15 are running before doing this!)*
Once the UI is running, upload the provided `.xlsx` product catalogue directly via the Dashboard UI ("Upload Excel" button).

## 14. Running the Application
If not using Docker or the `run_local.bat` script, run the Django server manually:
```bash
python manage.py runserver
```
Navigate to `http://localhost:8000/dashboard/`

## 15. Running Background Workers
If not using Docker or the `run_local.bat` script, ensure Redis is running (port 6379), then manually start Celery:
```bash
celery -A config worker -l info --pool=threads
```

## 16. Classification Flow
1. Text metadata is embedded locally and compared against 5,000+ taxonomy categories.
2. Top 10 candidate paths + Image (if available) are sent to the LLM.
3. LLM returns JSON containing the exact primary path, confidence, attributes, and alternatives.

## 17. Dashboard Usage
**Default Credentials:** Username: `admin` | Password: `admin123`
- View overall statistics (Total, Pending, Success, Failed, Manual Review).
- Click "Upload Excel" to ingest new products.
- Click "Process Pending" to trigger the Celery batch worker.
- Click any row to inspect, edit, or approve the classification.

## 18. API Endpoints
- `POST /api/upload/`: Ingest product Excel file.
- `POST /api/process-batch/`: Trigger background processing.
- `GET /api/classifications/`: Paginated results.
- `PATCH /api/classifications/<id>/`: Update/approve classification.

## 19. Batch Processing
Handled via a Celery queue. A `ProcessingJob` tracks progress. The worker pulls products individually, completely decoupled from the web UI.

## 20. Resume Behavior
The worker only queries products where `status='PENDING'`. If the server crashes, restarting the worker automatically resumes exactly where it left off, skipping completed products.

## 21. Error Handling
Each product is wrapped in a `try-except` block. If an image is broken (404) or an API times out, the failure is caught, the product is marked as `FAILED`, and the batch continues without stopping.

## 22. Manual Review
Products are flagged (`requires_manual_review = True`) if the confidence score is < 70%, if the candidate path is invalid, or if processing fails. Reviewers can easily select from alternative categories in the UI.

## 23. Screenshots
- **Dashboard View:** *(Add screenshot here)*
- **Manual Review Modal:** *(Add screenshot here)*
- **Demo Video:** *(Add link to Loom/YouTube here)*

## 24. Sample Results
An example of the extracted classification payload:
```json
{
  "primary_category": "Apparel & Accessories > Clothing > Shirts & Tops",
  "confidence_score": 95,
  "attributes": {
    "Material": "Cotton",
    "Color": "Blue"
  },
  "alternative_categories": [
    "Apparel & Accessories > Clothing > Activewear"
  ]
}
```

## 25. Limitations
- External LLM API rate limits (mitigated by text-only fallbacks).
- Initial local embeddings load time on worker startup (handled by lazy loading).

## 26. Production Improvements
- Migrate local `SentenceTransformers` to a dedicated Vector DB (Pinecone/Milvus).
- Implement WebSockets for real-time progress bars instead of AJAX polling.
- Deploy across AWS ECS (Fargate).

## 27. Testing
Run the test suite to verify models and APIs:
```bash
python manage.py test
```

## 28. Assignment Question Answers
Detailed answers to the 14 theoretical questions requested in the assignment can be found in [`CANDIDATE_ANSWERS.md`](./CANDIDATE_ANSWERS.md).
