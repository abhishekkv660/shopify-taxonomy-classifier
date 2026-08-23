# Candidate Answers

### 1. What approach would you use to automatically identify the Shopify category, attributes, and attribute values? Explain your approach and why you selected it.
My approach combines the speed of local semantic search with the reasoning power of Large Language Models. To avoid overwhelming the LLM with all 5,000+ taxonomy categories, I first use a local `SentenceTransformer` to retrieve the top 10 most semantically relevant candidate categories for a given product. I then pass these candidates, along with the product's metadata (and image context via Google Gemini Vision), into a highly optimized LLM prompt (via Groq/LLaMA3). The LLM is forced to return strict JSON containing the exact primary category and extracted attributes. This hybrid approach is selected because it is highly accurate, context-aware, and extremely fast.

### 2. How would you handle a product that has a title but no description and no image?
The system gracefully degrades. The local semantic search (`SentenceTransformer`) generates embeddings based purely on the Title. The LLM is also instructed to infer as much context as possible from the Title alone. While confidence scores may naturally be lower without descriptions or images, the system will still output the most logical primary category and flag it for manual review if the confidence drops below the acceptable threshold (70%).

### 3. How would you use product images to improve classification when an image is available?
I integrate Google's Gemini Pro Vision model. When a product has an image URL, the image is downloaded and passed to the vision model alongside the text metadata. The vision model can identify physical characteristics, materials, colors, and styles that are often entirely omitted from product titles and descriptions, leading to significantly richer attribute extraction and higher classification accuracy.

### 4. How would you design the application to process 10,000+ products efficiently? Explain your approach for batch/background processing.
I utilize **Celery** paired with **Redis** as a message broker. When a 10,000-product batch is uploaded, the Django web server immediately creates a `ProcessingJob` database record and queues the product IDs into Redis. A pool of asynchronous Celery worker threads then processes the products in the background. This entirely decouples the heavy ML inference from the web server, allowing the UI to remain highly responsive while processing happens iteratively behind the scenes.

### 5. How would you store the Shopify taxonomy and its category hierarchy in the database?
I store the taxonomy in a normalized relational structure using Django models (`TaxonomyCategory`). Each category is stored with its `shopify_id`, `name`, and `full_path`. To represent the hierarchy, I use a self-referential foreign key (`parent = models.ForeignKey('self')`), which allows the database to easily reconstruct trees, fetch subcategories, or query breadcrumbs.

### 6. How would you calculate or determine the confidence score for a classification?
The confidence score is generated natively by the LLM. The prompt explicitly instructs the LLM to evaluate the certainty of its categorization decision based on the provided context, and output an integer between 1 and 100. This is normalized to a 0.0-1.0 scale and saved directly in the database.

### 7. What would you do when the system cannot confidently identify a single category?
The LLM prompt includes a conditional instruction: `"If confidence_score < 80, provide 1 to 3 alternative_categories from the candidates."` The backend extracts these alternatives and saves them in an `AlternativeCategory` relational table. The product is also flagged as `requires_manual_review = True`, so human reviewers can easily select from the suggested alternatives via the dashboard UI.

### 8. How would you handle a broken or inaccessible product image without stopping the complete batch?
The Celery task loop processes each product within a strict `try-except` block. If an image request times out or returns a 404, the exception is caught, a warning is logged, and the system automatically falls back to text-only classification using Groq/LLaMA3. The product is processed successfully, and the batch continues uninterrupted.

### 9. How would you design the API and database structure for this application?
- **Database:** Normalized tables including `Product`, `TaxonomyCategory`, `TaxonomyAttribute`, `Classification` (linking products to categories with confidence scores), and `ProcessingJob` (tracking batch state).
- **API:** RESTful endpoints built with Django REST Framework.
  - `POST /api/jobs/`: Trigger a new batch job.
  - `GET /api/jobs/<id>/`: Poll job progress.
  - `GET /api/classifications/`: Fetch paginated, filterable classification results.
  - `PATCH /api/classifications/<id>/`: Allow human reviewers to update/approve classifications.

### 10. If the application needs to process 10,000 products and each external AI/API request takes approximately 2 seconds, how would you optimize the processing time?
A single thread taking 2s per product would take ~5.5 hours for 10,000 products. To optimize this, I use a **Thread Pool** within the Celery worker (`celery -A core worker --pool=threads --concurrency=20`). Since API requests are entirely I/O bound (waiting for network responses), we can safely run 20+ concurrent threads per worker. This effectively divides the processing time by 20, bringing the total time down to ~15 minutes without heavy CPU overhead.

### 11. How would you design the system so that if processing fails after 6,000 products, it can resume from the remaining products instead of starting again?
State management is handled in the database. Each product has a `status` field (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`). When a batch job starts, it only queries products where `status='PENDING'`. If the Celery worker crashes at 6,000 products, the next worker simply picks up the remaining 4,000 `PENDING` products. Database transactions ensure that statuses are committed atomically, preventing duplicate processing.

### 12. What technologies/frameworks would you choose for this application, and why?
- **Backend:** Python + Django (excellent ORM and rapid API development via DRF).
- **Background Processing:** Celery + Redis (industry standard, highly resilient task queues).
- **Database:** MariaDB (fully ACID compliant, excellent relational integrity).
- **AI/ML:** `sentence-transformers` for local RAG, Groq (LLaMA3) for hyper-fast text inference, Google Gemini for Vision.
- **Infrastructure:** Docker & Docker Compose (guarantees environment parity between development and production).

### 13. Provide a high-level architecture/design for the complete application.
The application follows a decoupled 3-tier architecture:
1. **Frontend Tier:** A Vanilla JS / HTML dashboard that consumes REST APIs.
2. **Web Tier:** A Django WSGI server handling HTTP requests, API authentication, and reading/writing to MariaDB.
3. **Worker Tier:** Asynchronous Celery workers pulling tasks from Redis. The workers handle the heavy lifting: downloading images, querying the local Vector space for candidates, making HTTP requests to external LLMs, and committing the final classifications back to MariaDB.

### 14. Provide a realistic development effort estimation in hours, including a task-wise breakdown for developing this as a production-ready application. Mention your assumptions and major dependencies/risks.

**Assumptions & Risks:**
- **Assumption:** Access to high-throughput LLM API keys (Groq/Gemini).
- **Risk:** API rate limiting. *Mitigation: Implemented exponential backoff and text-only fallbacks.*

**Total Estimated Effort: 40 Hours (5 Days)**
- **Day 1 (8 hrs): Architecture & Database Setup**
  - Django project scaffolding, MariaDB setup, and designing relational models.
  - Writing scripts to parse and normalize the Shopify taxonomy into the database.
- **Day 2 (8 hrs): Core ML Logic**
  - Implementing local `SentenceTransformers` for candidate retrieval.
  - Integrating Groq/LLaMA3 for text classification and Gemini for Vision processing.
- **Day 3 (8 hrs): Background Processing & Resilience**
  - Setting up Celery and Redis.
  - Writing idempotent task loops, error handling, and exponential backoffs.
- **Day 4 (8 hrs): API & Frontend Dashboard**
  - Building REST APIs with DRF.
  - Developing the Vanilla JS dashboard, progress bars, and manual review modal.
- **Day 5 (8 hrs): Containerization & Polish (What to do)**
  - Dockerizing the application, Redis, Celery, and MariaDB into a `docker-compose.yml`.
  - Final end-to-end testing, documentation (`README.md`), and UI polish.
