# OpenKeywords

AI-powered SEO keyword generation using a 5-stage pipeline with Google Gemini.

## Architecture

```
openkeyword/
├── api.py              # FastAPI REST API
├── run_pipeline.py     # Pipeline orchestrator
├── stage1/             # Company Analysis
├── stage2/             # Deep Research (Reddit, Quora)
├── stage3/             # AI Keyword Generation
├── stage4/             # Scoring & Deduplication
├── stage5/             # Clustering
└── tests/              # Test suite
```

## Pipeline Stages

| Stage | Name | Description |
|-------|------|-------------|
| 1 | Company Analysis | Analyzes company website using Gemini with Google Search grounding |
| 2 | Deep Research | Discovers keywords from Reddit, Quora, forums (optional) |
| 3 | AI Generation | Generates keywords using Gemini AI |
| 4 | Scoring | Scores keywords for company-fit, removes duplicates |
| 5 | Clustering | Groups keywords into semantic clusters |

## Quick Start

### Requirements

- Python 3.10+
- Google Gemini API key

### Installation

```bash
git clone https://github.com/federicodeponte/openkeyword.git
cd openkeyword
pip install -r requirements.txt
```

### Environment

```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### CLI Usage

```bash
# Generate keywords for a company
python run_pipeline.py --url https://stripe.com --count 50
python run_pipeline.py --url https://stripe.com --count 50 --output results/

# Output example:
# {
#   "company": "Stripe",
#   "keywords": 50,
#   "clusters": 6,
#   "avg_score": 85.2,
#   "duration": 25.3
# }

# With deep research enabled (Reddit/Quora)
python run_pipeline.py --url https://stripe.com --count 100 --research

# Custom settings
python run_pipeline.py --url https://notion.so --count 30 --min-score 50 --clusters 8
```

### API Usage

```bash
# Start the API server
uvicorn api:app --port 8001

# API docs available at http://localhost:8001/docs
```

#### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| POST | `/api/v1/jobs` | Create async generation job |
| GET | `/api/v1/jobs` | List all jobs |
| GET | `/api/v1/jobs/{id}` | Get job status/result |
| DELETE | `/api/v1/jobs/{id}` | Delete job |
| GET | `/api/v1/jobs/{id}/export/json` | Export as JSON |
| GET | `/api/v1/jobs/{id}/export/csv` | Export as CSV |
| POST | `/api/v1/generate` | Sync generation (≤100 keywords) |

#### Example API Call

```bash
curl -X POST http://localhost:8001/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Stripe",
    "company_url": "https://stripe.com",
    "target_count": 20
  }'
```

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | Yes | - | Google Gemini API key |

## Output

The pipeline returns:

```json
{
  "keywords": [
    {
      "keyword": "stripe payment integration",
      "intent": "transactional",
      "score": 92,
      "cluster_name": "Payment Integration",
      "is_question": false,
      "source": "ai_generated"
    }
  ],
  "clusters": [
    {
      "name": "Payment Integration",
      "keywords": ["stripe payment integration", "..."],
      "count": 5
    }
  ],
  "statistics": {
    "total_keywords": 50,
    "avg_score": 85.2,
    "duration_seconds": 25.3
  }
}
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_api.py -v
```

## License

MIT
