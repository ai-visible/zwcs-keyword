# 🔑 OpenKeywords

**AI-powered SEO keyword generation using Gemini + SE Ranking**

Generate high-quality, clustered SEO keywords for any business in seconds.

## ✨ Features

- **AI Keyword Generation** - Uses Google Gemini to generate relevant keywords
- **Intent Classification** - Automatic classification (informational, commercial, transactional, question, comparison)
- **Company-Fit Scoring** - AI scores each keyword's relevance to your business (0-100)
- **Semantic Clustering** - Groups keywords into topic clusters for content planning
- **Deduplication** - Removes exact and near-duplicate keywords
- **SE Ranking Integration** - Optional real search volume & difficulty data via SE Ranking API
- **Multi-language Support** - Generate keywords in any language/region

## 🚀 Quick Start

### Installation

```bash
pip install openkeywords
```

Or install from source:

```bash
git clone https://github.com/scaile/openkeywords.git
cd openkeywords
pip install -e .
```

### Set API Keys

```bash
export GEMINI_API_KEY="your-gemini-api-key"
export SERANKING_API_KEY="your-seranking-key"  # Optional
```

### CLI Usage

```bash
# Basic generation
openkeywords generate \
  --company "Acme Software" \
  --industry "B2B SaaS" \
  --services "project management,team collaboration" \
  --count 50

# With SE Ranking volume data
openkeywords generate \
  --company "Acme Software" \
  --url "https://acme.com" \
  --count 50 \
  --with-volume

# Output to file
openkeywords generate \
  --company "Acme Software" \
  --count 50 \
  --output keywords.csv
```

### Python Usage

```python
from openkeywords import KeywordGenerator, CompanyInfo

# Initialize generator
generator = KeywordGenerator(
    gemini_api_key="your-key",  # or uses GEMINI_API_KEY env var
    seranking_api_key="your-key",  # optional
)

# Define company
company = CompanyInfo(
    name="Acme Software",
    industry="B2B SaaS",
    services=["project management", "team collaboration"],
    target_audience="small businesses",
    target_location="United States",
)

# Generate keywords
result = await generator.generate(
    company_info=company,
    target_count=50,
    language="english",
    region="us",
    enable_clustering=True,
    cluster_count=5,
)

# Access results
for kw in result.keywords:
    print(f"{kw.keyword} | {kw.intent} | Score: {kw.score}")

# Export to CSV
result.to_csv("keywords.csv")

# Export to JSON
result.to_json("keywords.json")
```

## 📊 Output Format

### Keywords

| Field | Description |
|-------|-------------|
| `keyword` | The keyword text |
| `intent` | Search intent: `informational`, `commercial`, `transactional`, `question`, `comparison` |
| `score` | Company-fit score (0-100) |
| `cluster_name` | Semantic cluster grouping |
| `is_question` | Boolean - is this a question-based keyword? |
| `volume` | Monthly search volume (if SE Ranking enabled) |
| `difficulty` | SEO difficulty score (if SE Ranking enabled) |

### Example Output

```json
{
  "keywords": [
    {
      "keyword": "best project management software for small teams",
      "intent": "commercial",
      "score": 87,
      "cluster_name": "Product Comparison",
      "is_question": false,
      "volume": 1200,
      "difficulty": 45
    },
    {
      "keyword": "how to improve team collaboration remotely",
      "intent": "question",
      "score": 72,
      "cluster_name": "How-To Guides",
      "is_question": true,
      "volume": 890,
      "difficulty": 32
    }
  ],
  "clusters": [
    {"name": "Product Comparison", "count": 12},
    {"name": "How-To Guides", "count": 8},
    {"name": "Industry Solutions", "count": 15}
  ],
  "statistics": {
    "total": 50,
    "avg_score": 71.4,
    "intent_breakdown": {
      "commercial": 15,
      "informational": 12,
      "question": 10,
      "transactional": 8,
      "comparison": 5
    }
  }
}
```

## ⚙️ Configuration

### Generation Config

```python
from openkeywords import GenerationConfig

config = GenerationConfig(
    target_count=50,           # Number of keywords to generate
    min_score=40,              # Minimum company-fit score
    enable_clustering=True,    # Group keywords into clusters
    cluster_count=6,           # Target number of clusters
    language="english",        # Target language
    region="us",               # Target region (country code)
    enable_volume=False,       # Fetch SE Ranking volume data
)
```

### Intent Distribution

The generator aims for a balanced distribution:
- **25%** Question keywords (AEO-optimized)
- **25%** Commercial keywords (best, top, review)
- **15%** Transactional keywords (buy, sign up, get)
- **10%** Comparison keywords (vs, alternative)
- **25%** Informational keywords (guides, tips)

### Word Length Distribution

Keywords are balanced by length:
- **20%** Short (2-3 words) - e.g., "project management"
- **50%** Medium (4-5 words) - e.g., "best project management software"
- **30%** Long (6-7 words) - e.g., "how to choose project management tool"

## 🔌 SE Ranking Integration

SE Ranking provides real search volume and difficulty metrics.

```python
# Enable SE Ranking
generator = KeywordGenerator(
    gemini_api_key="...",
    seranking_api_key="your-seranking-key",
)

# Generate with volume data
result = await generator.generate(
    company_info=company,
    target_count=50,
    enable_volume=True,  # Fetches SE Ranking data
)
```

Without SE Ranking, `volume` and `difficulty` will be `0`.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      OpenKeywords                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. GENERATION (Gemini)                                     │
│     └─ AI generates diverse keywords with intent            │
│                                                              │
│  2. DEDUPLICATION                                           │
│     └─ Remove exact + near-duplicates (O(n) algorithm)      │
│                                                              │
│  3. SCORING (Gemini)                                        │
│     └─ Score company fit (0-100)                            │
│                                                              │
│  4. VOLUME DATA (SE Ranking) [Optional]                     │
│     └─ Fetch real search volume & difficulty                │
│                                                              │
│  5. CLUSTERING (Gemini)                                     │
│     └─ Group into semantic clusters                         │
│                                                              │
│  6. FILTERING                                               │
│     └─ Apply min_score, enforce distributions               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

## 🤝 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

## 🔗 Links

- [Documentation](https://github.com/scaile/openkeywords)
- [SE Ranking API](https://seranking.com/api-documentation.html)
- [Google Gemini](https://ai.google.dev/)


