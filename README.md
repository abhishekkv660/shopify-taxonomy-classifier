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
- Docker
- Docker Compose

## 8. Database Configuration
Docker will automatically initialize a MariaDB instance (`taxonomy_db`) using the default credentials configured in your `.env` file.

## 9. Environment Variables
Create a `.env` file in the root directory:
```env
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key
DB_NAME=taxonomy_db
DB_USER=taxonomy_user
DB_PASSWORD=your_password
```

## 10. Installation & Startup

To launch the entire stack (Database, Redis, Celery Worker, and Django API) in one click, run:
```bash
docker-compose up --build
```
*Note: On first startup, the system will automatically run migrations, auto-provision the default `admin` account, and seed the entire Shopify taxonomy into the database. This takes ~2 minutes.*

## 11. Product Import
Once the UI is running, navigate to `http://localhost:8000/dashboard/`. Upload the provided `.xlsx` product catalogue directly via the Dashboard UI ("Upload Excel" button).

## 12. Classification Flow
1. Text metadata is embedded locally and compared against 5,000+ taxonomy categories.
2. Top 10 candidate paths + Image (if available) are sent to the LLM.
3. LLM returns JSON containing the exact primary path, confidence, attributes, and alternatives.

## 13. Dashboard Usage
**Default Credentials:** Username: `admin` | Password: `admin123`
- View overall statistics (Total, Pending, Success, Failed, Manual Review).
- Click "Upload Excel" to ingest new products.
- Click "Process Pending" to trigger the Celery batch worker.
- Click any row to inspect, edit, or approve the classification.

## 14. API Endpoints
- `POST /api/upload/`: Ingest product Excel file.
- `POST /api/process-batch/`: Trigger background processing.
- `GET /api/classifications/`: Paginated results.
- `PATCH /api/classifications/<id>/`: Update/approve classification.

## 15. Batch Processing
Handled via a Celery queue. A `ProcessingJob` tracks progress. The worker pulls products individually, completely decoupled from the web UI.

## 16. Resume Behavior
The worker only queries products where `status='PENDING'`. If the server crashes, restarting the worker automatically resumes exactly where it left off, skipping completed products.

## 17. Error Handling
Each product is wrapped in a `try-except` block. If an image is broken (404) or an API times out, the failure is caught, the product is marked as `FAILED`, and the batch continues without stopping.

## 18. Manual Review
Products are flagged (`requires_manual_review = True`) if the confidence score is < 70%, if the candidate path is invalid, or if processing fails. Reviewers can easily select from alternative categories in the UI.

## 19. Screenshots
- **Dashboard View:** *(Add screenshot here)*
- **Manual Review Modal:** *(Add screenshot here)*
- **Demo Video:** *(Add link to Loom/YouTube here)*

## 20. Sample Results
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

## 21. Limitations
- External LLM API rate limits (mitigated by text-only fallbacks).
- Initial local embeddings load time on worker startup (handled by lazy loading).

## 22. Production Improvements
- Migrate local `SentenceTransformers` to a dedicated Vector DB (Pinecone/Milvus).
- Implement WebSockets for real-time progress bars instead of AJAX polling.
- Deploy across AWS ECS (Fargate).

## 23. Testing
Run the test suite inside the docker container:
```bash
docker-compose exec web python manage.py test
```

## 24. Assignment Question Answers
Detailed answers to the 14 theoretical questions requested in the assignment can be found in [`CANDIDATE_ANSWERS.md`](./CANDIDATE_ANSWERS.md).
