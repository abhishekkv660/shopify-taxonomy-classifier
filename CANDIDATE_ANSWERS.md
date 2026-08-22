# Candidate Answers

### 1. Briefly explain your approach to the problem.
My approach focused on combining the speed of local semantic search with the reasoning power of Large Language Models. To avoid overwhelming the LLM with 5,000+ taxonomy categories, I first use a local `SentenceTransformer` to retrieve the top 10 most semantically relevant candidate categories for a given product. I then pass these candidates, along with the product's metadata (and image context via Google Gemini Vision), into a highly optimized LLM prompt (via Groq/LLaMA3). The LLM is forced to return strict JSON containing the exact primary category, confidence score, and extracted attributes.

### 2. How did you handle the Shopify taxonomy mapping?
I parsed the raw `taxonomy.txt` file and loaded it into a normalized relational database (`TaxonomyCategory` and `TaxonomyAttribute` models). During candidate retrieval, the LLM is strictly constrained to only output category paths that exactly match one of the candidate paths provided to it, guaranteeing 100% compliance with the official Shopify taxonomy.

### 3. What strategy did you use for candidate category generation?
I used `SentenceTransformers` (`all-MiniLM-L6-v2`) to pre-compute embeddings for all 5,000+ Shopify category paths. When a product is processed, I generate an embedding for the product's Title + Description and perform a Cosine Similarity search against the taxonomy embeddings to fetch the top 10 closest matches.

### 4. How were attributes extracted?
Attribute extraction was bundled into the LLM classification prompt. Once the LLM decides on a primary category, it is instructed to analyze the product description and title to extract relevant key-value pairs (e.g., `"Material": "Wood"`, `"Brand": "Modway"`). These are parsed from the JSON response and mapped to the normalized `TaxonomyAttribute` table where possible.

### 5. How did you calculate the confidence score?
The confidence score is generated natively by the LLM. The prompt explicitly instructs the LLM to evaluate the certainty of its categorization decision and output an integer between 1 and 100. This is normalized to a 0.0-1.0 scale and saved in the database.

### 6. Describe your logic for alternative category suggestions.
The LLM prompt includes a conditional instruction: `"If confidence_score < 80, provide 1 to 3 alternative_categories from the candidates."` The backend extracts these alternatives from the JSON payload and saves them in the `AlternativeCategory` database table, ranked by relevance, which are then exposed to the dashboard UI for human reviewers.

### 7. How does your system flag products for manual review?
A product is automatically flagged for manual review (`requires_manual_review = True`) if the LLM's confidence score drops below 70%, or if the LLM entirely fails to match an exact primary category path, or if an API rate-limit failure occurs.

### 8. Explain how your application handles batch processing for 10k+ products.
I utilized **Celery** and **Redis** to create an asynchronous background worker. When the user clicks "Start Batch Processor" on the UI, the Django API creates a persistent `ProcessingJob` in the database and queues a Celery task containing the unclassified product IDs. The worker processes the queue iteratively in the background, entirely decoupling the heavy LLM inference from the web request lifecycle.

### 9. What steps did you take to ensure the process continues despite failures?
The Celery loop is wrapped in a strict `try-except` block per product. If an individual product fails (e.g., due to an invalid image URL or a malformed JSON response), the error is logged, the product is flagged as `FAILED`, and the worker immediately continues to the next product in the batch. Additionally, `vision_analyzer.py` catches HTTP 429 Rate Limits from Gemini and gracefully falls back to text-only processing.

### 10. How did you structure your API?
The API is built using Django REST Framework. It provides clean endpoints for triggering jobs (`POST /api/process-batch/`), checking job progress (`GET /api/job-status/`), and paginated CRUD operations for the UI (`GET /api/classifications/` and `PATCH /api/classifications/<id>/`).

### 11. Briefly describe the UI/Dashboard you built.
I built a modern, responsive single-page application using Vanilla JS and pure CSS (avoiding heavy frontend frameworks). It features a real-time progress bar for batch jobs, KPI stat cards (Total Catalog, Pending, Needs Review), and a paginated data table. Clicking a product opens an intuitive inspection modal containing a searchable Category dropdown for editing, and text inputs for tweaking extracted attributes before approval.

### 12. What were the biggest challenges you faced and how did you solve them?
The biggest challenge was hitting API rate limits with the Google Gemini Vision API when processing large batches rapidly. To solve this, I implemented an exponential backoff / graceful fallback mechanism. If Gemini throws a 429 error, the system catches it, logs a warning, and dynamically falls back to standard text-only LLM classification without dropping the product.

### 13. How would you scale this application to handle 1 million+ products?
To handle 1M+ products, I would scale horizontally:
1. Increase the number of Celery workers running across multiple EC2 instances or Kubernetes pods.
2. Upgrade the local `SentenceTransformers` search to a dedicated Vector Database like Pinecone or Milvus.
3. Batch the LLM requests using a high-throughput provider like vLLM on dedicated GPUs, rather than relying on standard third-party rate-limited APIs.

### 14. What would you do differently if you had more time?
If I had more time, I would implement WebSockets (via Django Channels) to stream real-time progress updates to the UI, rather than relying on Javascript AJAX polling. I would also add an Active Learning feedback loop, where manually corrected classifications are used to automatically fine-tune the local embeddings model over time.

### 15. How would you deploy this to AWS or GCP?
For AWS deployment:
- **Compute:** Deploy the Django web app and Celery workers on AWS ECS (Fargate) for scalable container orchestration.
- **Database:** Use Amazon RDS (PostgreSQL) for persistent relational data.
- **Message Broker:** Use Amazon ElastiCache (Redis) to queue Celery tasks.
- **Storage:** Store uploaded Excel files and static assets in an S3 bucket served by CloudFront.
- **Load Balancing:** Put the ECS web tasks behind an Application Load Balancer (ALB).
