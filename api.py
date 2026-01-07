"""
OpenKeywords API - FastAPI Application

RESTful API wrapper for the keyword generation pipeline.

Usage:
    uvicorn api:app --reload --port 8001

API Docs:
    - Swagger UI: http://localhost:8001/docs
    - ReDoc: http://localhost:8001/redoc
    - OpenAPI JSON: http://localhost:8001/openapi.json
"""

import asyncio
import os
import threading
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Path, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, HttpUrl, field_validator

from openkeywords import (
    CompanyInfo,
    GenerationConfig,
    GenerationResult,
    KeywordGenerator,
)

# =============================================================================
# Pydantic Models for API
# =============================================================================


class JobStatus(str, Enum):
    """Job status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class KeywordRequest(BaseModel):
    """Request model for keyword generation."""

    company_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Company name",
        json_schema_extra={"example": "Acme Software"},
    )
    company_url: Optional[HttpUrl] = Field(
        default=None,
        description="Company website URL (enables gap analysis)",
        json_schema_extra={"example": "https://example.com"},
    )
    industry: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Industry category",
        json_schema_extra={"example": "B2B SaaS"},
    )
    description: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Company description",
        json_schema_extra={"example": "AI-powered marketing automation platform"},
    )
    services: List[str] = Field(
        default=[],
        max_length=20,
        description="Services offered (max 20)",
        json_schema_extra={"example": ["marketing automation", "analytics"]},
    )
    products: List[str] = Field(
        default=[],
        max_length=20,
        description="Products offered (max 20)",
        json_schema_extra={"example": ["Marketing Hub", "Analytics Dashboard"]},
    )
    target_audience: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Target audience description",
        json_schema_extra={"example": "SMB marketing teams"},
    )
    target_location: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Target location/region",
        json_schema_extra={"example": "United States"},
    )
    competitors: List[str] = Field(
        default=[],
        max_length=10,
        description="Competitor URLs (max 10)",
        json_schema_extra={"example": ["https://competitor1.com"]},
    )
    # Generation config
    target_count: int = Field(
        default=50,
        ge=10,
        le=500,
        description="Number of keywords to generate (10-500)",
    )
    cluster_count: int = Field(
        default=6,
        ge=1,
        le=20,
        description="Number of keyword clusters (1-20)",
    )
    min_score: int = Field(
        default=40,
        ge=0,
        le=100,
        description="Minimum company-fit score (0-100)",
    )
    language: str = Field(
        default="english",
        max_length=50,
        description="Target language",
        json_schema_extra={"example": "english"},
    )
    region: str = Field(
        default="us",
        max_length=10,
        pattern=r"^[a-z]{2}$",
        description="Target region code (ISO 3166-1 alpha-2)",
        json_schema_extra={"example": "us"},
    )
    # Feature flags
    enable_research: bool = Field(
        default=False,
        description="Enable deep research (Reddit, Quora, forums)",
    )
    research_focus: bool = Field(
        default=False,
        description="Agency mode: 70%+ research keywords, strict filtering",
    )
    enable_serp_analysis: bool = Field(
        default=False,
        description="Enable SERP analysis for AEO scoring",
    )
    serp_sample_size: int = Field(
        default=15,
        ge=1,
        le=50,
        description="Keywords to SERP analyze (1-50)",
    )
    enable_volume_lookup: bool = Field(
        default=False,
        description="Get real search volumes from DataForSEO",
    )
    analyze_company_first: bool = Field(
        default=False,
        description="Auto-analyze company website for rich context (requires company_url)",
    )

    @field_validator("services", "products")
    @classmethod
    def validate_list_items(cls, v: List[str]) -> List[str]:
        """Validate list items are non-empty."""
        return [item.strip() for item in v if item and item.strip()]

    @field_validator("competitors")
    @classmethod
    def validate_competitors(cls, v: List[str]) -> List[str]:
        """Validate competitor URLs."""
        validated = []
        for url in v:
            url = url.strip()
            if url:
                if not url.startswith(("http://", "https://")):
                    url = f"https://{url}"
                validated.append(url)
        return validated[:10]  # Max 10 competitors


class KeywordResponse(BaseModel):
    """Response model for a single keyword."""

    keyword: str
    intent: str
    score: int
    cluster_name: Optional[str] = None
    is_question: bool = False
    volume: int = 0
    difficulty: int = 50
    source: str = "ai_generated"
    aeo_opportunity: int = 0
    has_featured_snippet: bool = False
    has_paa: bool = False
    serp_analyzed: bool = False


class ClusterResponse(BaseModel):
    """Response model for a keyword cluster."""

    name: str
    keywords: List[str]
    count: int


class StatisticsResponse(BaseModel):
    """Response model for generation statistics."""

    total: int
    avg_score: float
    intent_breakdown: Dict[str, int]
    source_breakdown: Dict[str, int]
    duplicate_count: int = 0


class GenerationResultResponse(BaseModel):
    """Response model for generation result."""

    keywords: List[KeywordResponse]
    clusters: List[ClusterResponse]
    statistics: StatisticsResponse
    processing_time_seconds: float


class JobResponse(BaseModel):
    """Response model for job creation."""

    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status")
    message: str = Field(..., description="Status message")
    created_at: str = Field(..., description="Job creation timestamp")


class JobStatusResponse(BaseModel):
    """Response model for job status check."""

    job_id: str
    status: JobStatus
    progress: Optional[Dict[str, Any]] = Field(None, description="Progress details")
    result: Optional[GenerationResultResponse] = Field(
        None, description="Generation result (when completed)"
    )
    error: Optional[str] = Field(None, description="Error message (when failed)")
    created_at: str
    updated_at: str


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str = "1.0.0"
    timestamp: str
    gemini_configured: bool = False
    seranking_configured: bool = False
    dataforseo_configured: bool = False


# =============================================================================
# In-Memory Job Store (replace with Redis/DB in production)
# =============================================================================


class JobStore:
    """Thread-safe in-memory job store."""

    def __init__(self):
        self._jobs: Dict[str, dict] = {}
        self._lock = threading.Lock()

    def create(self, job_id: str, request: KeywordRequest) -> dict:
        job = {
            "job_id": job_id,
            "status": JobStatus.PENDING,
            "request": request.model_dump(),
            "progress": {"keywords_generated": 0, "target_count": request.target_count},
            "result": None,
            "error": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        with self._lock:
            self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> Optional[dict]:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **kwargs) -> Optional[dict]:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(kwargs)
                self._jobs[job_id]["updated_at"] = datetime.utcnow().isoformat()
                return self._jobs[job_id]
        return None

    def list_all(self, limit: int = 50) -> List[dict]:
        with self._lock:
            jobs = sorted(
                self._jobs.values(), key=lambda x: x["created_at"], reverse=True
            )
            return jobs[:limit]

    def delete(self, job_id: str) -> bool:
        with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
                return True
        return False

    def cleanup_old_jobs(self, max_age_hours: int = 24, max_jobs: int = 1000) -> int:
        """Remove old jobs to prevent memory leak. Returns count of removed jobs."""
        from datetime import datetime, timedelta

        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        removed = 0

        with self._lock:
            # Remove jobs older than max_age_hours
            old_jobs = [
                job_id for job_id, job in self._jobs.items()
                if datetime.fromisoformat(job["created_at"]) < cutoff
            ]
            for job_id in old_jobs:
                del self._jobs[job_id]
                removed += 1

            # If still over max_jobs, remove oldest
            if len(self._jobs) > max_jobs:
                sorted_jobs = sorted(
                    self._jobs.items(),
                    key=lambda x: x[1]["created_at"]
                )
                excess = len(self._jobs) - max_jobs
                for job_id, _ in sorted_jobs[:excess]:
                    del self._jobs[job_id]
                    removed += 1

        return removed


def _validate_job_id(job_id: str) -> str:
    """Validate job_id is a valid UUID to prevent injection."""
    try:
        uuid.UUID(job_id)
        return job_id
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job_id format (must be UUID)")


def _sanitize_csv_value(value: Any) -> str:
    """Sanitize value for CSV to prevent formula injection."""
    str_val = str(value)
    # Prefix with single quote if starts with formula characters
    if str_val and str_val[0] in ('=', '+', '-', '@', '\t', '\r'):
        return f"'{str_val}"
    return str_val


# Global job store
job_store = JobStore()


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="OpenKeywords API",
    description="""
## AI-Powered SEO Keyword Generation

OpenKeywords generates high-quality, clustered SEO keywords using Google's Gemini AI.

### Features

- 🤖 **AI Generation**: Gemini-powered keyword generation with diverse intents
- 🔍 **Deep Research**: Reddit, Quora, forum analysis for hyper-niche keywords
- 📊 **Gap Analysis**: SE Ranking competitor keyword analysis
- 📈 **SERP Analysis**: AEO opportunity scoring with featured snippet detection
- 🎯 **Company-Fit Scoring**: Keywords scored 0-100 for relevance
- 📦 **Semantic Clustering**: Auto-grouped keywords by topic

### Pipeline Stages

1. **Company Analysis** (optional) - Auto-extract company context from website
2. **Research** (optional) - Deep dive into Reddit, Quora, forums
3. **Gap Analysis** (optional) - Find competitor keyword opportunities
4. **AI Generation** - Gemini-powered keyword creation
5. **SERP Analysis** (optional) - AEO scoring and featured snippet detection
6. **Scoring & Clustering** - Company-fit scoring and semantic grouping

### Export Formats

- JSON (full data with all metadata)
- CSV (flat format for spreadsheets)
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "OpenKeywords",
        "url": "https://github.com/federicodeponte/openkeyword",
    },
    license_info={
        "name": "MIT",
    },
)


# =============================================================================
# Background Task Runner
# =============================================================================


def _result_to_response(result: GenerationResult) -> dict:
    """Convert GenerationResult to API response dict."""
    return {
        "keywords": [
            {
                "keyword": kw.keyword,
                "intent": kw.intent,
                "score": kw.score,
                "cluster_name": kw.cluster_name,
                "is_question": kw.is_question,
                "volume": kw.volume,
                "difficulty": kw.difficulty,
                "source": kw.source,
                "aeo_opportunity": kw.aeo_opportunity,
                "has_featured_snippet": kw.has_featured_snippet,
                "has_paa": kw.has_paa,
                "serp_analyzed": kw.serp_analyzed,
            }
            for kw in result.keywords
        ],
        "clusters": [
            {"name": c.name, "keywords": c.keywords, "count": c.count}
            for c in result.clusters
        ],
        "statistics": {
            "total": result.statistics.total,
            "avg_score": result.statistics.avg_score,
            "intent_breakdown": result.statistics.intent_breakdown,
            "source_breakdown": result.statistics.source_breakdown,
            "duplicate_count": result.statistics.duplicate_count,
        },
        "processing_time_seconds": result.processing_time_seconds,
    }


async def run_generation_job(job_id: str, request: KeywordRequest):
    """Background task to run keyword generation."""
    try:
        job_store.update(job_id, status=JobStatus.RUNNING)

        # Build CompanyInfo
        company_info = CompanyInfo(
            name=request.company_name,
            url=str(request.company_url) if request.company_url else "",
            industry=request.industry,
            description=request.description,
            services=request.services,
            products=request.products,
            target_audience=request.target_audience,
            target_location=request.target_location,
            competitors=request.competitors,
        )

        # Auto-analyze company if requested
        if request.analyze_company_first and request.company_url:
            try:
                from openkeywords.company_analyzer import analyze_company

                analysis = await analyze_company(str(request.company_url))

                # Merge analysis results
                company_info.name = company_info.name or analysis.get(
                    "company_name", "Unknown"
                )
                company_info.industry = company_info.industry or analysis.get(
                    "industry"
                )
                company_info.description = company_info.description or analysis.get(
                    "description"
                )
                company_info.products = company_info.products or analysis.get(
                    "products", []
                )
                company_info.services = company_info.services or analysis.get(
                    "services", []
                )
                company_info.pain_points = analysis.get("pain_points", [])
                company_info.customer_problems = analysis.get("customer_problems", [])
                company_info.use_cases = analysis.get("use_cases", [])
                company_info.value_propositions = analysis.get("value_propositions", [])
                company_info.differentiators = analysis.get("differentiators", [])
                company_info.key_features = analysis.get("key_features", [])
                company_info.solution_keywords = analysis.get("solution_keywords", [])
                company_info.brand_voice = analysis.get("brand_voice")
            except Exception as e:
                # Log but don't fail - continue without analysis
                pass

        # Build GenerationConfig
        config = GenerationConfig(
            target_count=request.target_count,
            min_score=request.min_score,
            enable_clustering=True,
            cluster_count=request.cluster_count,
            language=request.language,
            region=request.region,
            enable_research=request.enable_research or request.research_focus,
            research_focus=request.research_focus,
            enable_serp_analysis=request.enable_serp_analysis,
            serp_sample_size=request.serp_sample_size,
            enable_volume_lookup=request.enable_volume_lookup,
        )

        # Run generation
        generator = KeywordGenerator()
        result = await generator.generate(company_info, config)

        # Convert to response format
        result_dict = _result_to_response(result)

        job_store.update(
            job_id,
            status=JobStatus.COMPLETED,
            result=result_dict,
            progress={
                "keywords_generated": len(result.keywords),
                "target_count": request.target_count,
            },
        )

    except Exception as e:
        job_store.update(job_id, status=JobStatus.FAILED, error=str(e))


# =============================================================================
# API Endpoints
# =============================================================================


@app.get(
    "/",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health check",
)
async def health_check():
    """Check API health status and configuration."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat(),
        gemini_configured=bool(os.getenv("GEMINI_API_KEY")),
        seranking_configured=bool(os.getenv("SERANKING_API_KEY")),
        dataforseo_configured=bool(
            os.getenv("DATAFORSEO_LOGIN") and os.getenv("DATAFORSEO_PASSWORD")
        ),
    )


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health check (alias)",
)
async def health():
    """Health check endpoint (alias for root)."""
    return await health_check()


@app.post(
    "/api/v1/jobs",
    response_model=JobResponse,
    status_code=202,
    tags=["Jobs"],
    summary="Start a new keyword generation job",
)
async def create_job(
    request: KeywordRequest,
    background_tasks: BackgroundTasks,
):
    """
    Start a new keyword generation job.

    The job runs asynchronously in the background. Use the returned `job_id`
    to check status via `GET /api/v1/jobs/{job_id}`.

    **Example request:**
    ```json
    {
        "company_name": "Acme Software",
        "company_url": "https://acme.com",
        "industry": "B2B SaaS",
        "target_count": 100,
        "enable_research": true
    }
    ```
    """
    # Check API key
    if not os.getenv("GEMINI_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="GEMINI_API_KEY not configured. Set environment variable.",
        )

    job_id = str(uuid.uuid4())
    job = job_store.create(job_id, request)

    # Start background task
    background_tasks.add_task(run_generation_job, job_id, request)

    return JobResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        message=f"Job created. Generating {request.target_count} keywords for '{request.company_name}'.",
        created_at=job["created_at"],
    )


@app.get(
    "/api/v1/jobs",
    response_model=List[JobStatusResponse],
    tags=["Jobs"],
    summary="List all jobs",
)
async def list_jobs(
    limit: int = Query(default=50, ge=1, le=100, description="Max jobs to return"),
):
    """List all keyword generation jobs, sorted by creation time (newest first)."""
    jobs = job_store.list_all(limit=limit)
    return [
        JobStatusResponse(
            job_id=job["job_id"],
            status=job["status"],
            progress=job.get("progress"),
            result=None,  # Don't include full result in list view
            error=job.get("error"),
            created_at=job["created_at"],
            updated_at=job["updated_at"],
        )
        for job in jobs
    ]


@app.get(
    "/api/v1/jobs/{job_id}",
    response_model=JobStatusResponse,
    tags=["Jobs"],
    summary="Get job status",
)
async def get_job(job_id: str = Path(..., description="Job UUID")):
    """
    Get the status and result of a keyword generation job.

    Returns full result when job is completed.
    """
    _validate_job_id(job_id)
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return JobStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        progress=job.get("progress"),
        result=job.get("result"),
        error=job.get("error"),
        created_at=job["created_at"],
        updated_at=job["updated_at"],
    )


@app.delete(
    "/api/v1/jobs/{job_id}",
    status_code=204,
    tags=["Jobs"],
    summary="Delete a job",
)
async def delete_job(job_id: str = Path(..., description="Job UUID")):
    """Delete a job and its results."""
    _validate_job_id(job_id)
    if not job_store.delete(job_id):
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return None


@app.get(
    "/api/v1/jobs/{job_id}/export/json",
    tags=["Export"],
    summary="Export keywords as JSON",
)
async def export_json(job_id: str = Path(..., description="Job UUID")):
    """Export keywords from a completed job as JSON."""
    _validate_job_id(job_id)
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job["status"] != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed")

    return JSONResponse(
        content=job.get("result", {}),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="keywords_{job_id[:8]}.json"'
        },
    )


@app.get(
    "/api/v1/jobs/{job_id}/export/csv",
    tags=["Export"],
    summary="Export keywords as CSV",
)
async def export_csv(job_id: str = Path(..., description="Job UUID")):
    """Export keywords from a completed job as CSV."""
    import csv
    import io

    _validate_job_id(job_id)
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job["status"] != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed")

    result = job.get("result", {})
    keywords = result.get("keywords", [])

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Headers
    headers = [
        "keyword",
        "intent",
        "score",
        "cluster",
        "is_question",
        "volume",
        "difficulty",
        "source",
        "aeo_opportunity",
        "has_featured_snippet",
        "has_paa",
    ]
    writer.writerow(headers)

    # Data (sanitized to prevent CSV formula injection)
    for kw in keywords:
        writer.writerow(
            [
                _sanitize_csv_value(kw.get("keyword", "")),
                _sanitize_csv_value(kw.get("intent", "")),
                kw.get("score", 0),
                _sanitize_csv_value(kw.get("cluster_name", "")),
                kw.get("is_question", False),
                kw.get("volume", 0),
                kw.get("difficulty", 50),
                _sanitize_csv_value(kw.get("source", "")),
                kw.get("aeo_opportunity", 0),
                kw.get("has_featured_snippet", False),
                kw.get("has_paa", False),
            ]
        )

    csv_content = output.getvalue()

    from fastapi.responses import Response

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="keywords_{job_id[:8]}.csv"'
        },
    )


@app.post(
    "/api/v1/generate",
    response_model=GenerationResultResponse,
    tags=["Sync"],
    summary="Generate keywords (synchronous)",
)
async def generate_sync(request: KeywordRequest):
    """
    Generate keywords synchronously (blocking).

    **Warning:** This endpoint blocks until generation completes.
    For large batches (>100 keywords), use the async job endpoint instead.

    Returns the full generation result directly.
    """
    # Check API key
    if not os.getenv("GEMINI_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="GEMINI_API_KEY not configured. Set environment variable.",
        )

    if request.target_count > 100:
        raise HTTPException(
            status_code=400,
            detail="Synchronous generation limited to 100 keywords. Use /api/v1/jobs for larger batches.",
        )

    # Build CompanyInfo
    company_info = CompanyInfo(
        name=request.company_name,
        url=str(request.company_url) if request.company_url else "",
        industry=request.industry,
        description=request.description,
        services=request.services,
        products=request.products,
        target_audience=request.target_audience,
        target_location=request.target_location,
        competitors=request.competitors,
    )

    # Auto-analyze if requested
    if request.analyze_company_first and request.company_url:
        try:
            from openkeywords.company_analyzer import analyze_company

            analysis = await analyze_company(str(request.company_url))
            company_info.name = company_info.name or analysis.get(
                "company_name", "Unknown"
            )
            company_info.industry = company_info.industry or analysis.get("industry")
            company_info.description = company_info.description or analysis.get(
                "description"
            )
            company_info.products = company_info.products or analysis.get(
                "products", []
            )
            company_info.services = company_info.services or analysis.get(
                "services", []
            )
            company_info.pain_points = analysis.get("pain_points", [])
            company_info.value_propositions = analysis.get("value_propositions", [])
            company_info.differentiators = analysis.get("differentiators", [])
        except Exception:
            pass  # Continue without analysis

    # Build config
    config = GenerationConfig(
        target_count=request.target_count,
        min_score=request.min_score,
        enable_clustering=True,
        cluster_count=request.cluster_count,
        language=request.language,
        region=request.region,
        enable_research=request.enable_research or request.research_focus,
        research_focus=request.research_focus,
        enable_serp_analysis=request.enable_serp_analysis,
        serp_sample_size=request.serp_sample_size,
        enable_volume_lookup=request.enable_volume_lookup,
    )

    # Run generation
    generator = KeywordGenerator()
    result = await generator.generate(company_info, config)

    # Convert to response
    return GenerationResultResponse(
        keywords=[
            KeywordResponse(
                keyword=kw.keyword,
                intent=kw.intent,
                score=kw.score,
                cluster_name=kw.cluster_name,
                is_question=kw.is_question,
                volume=kw.volume,
                difficulty=kw.difficulty,
                source=kw.source,
                aeo_opportunity=kw.aeo_opportunity,
                has_featured_snippet=kw.has_featured_snippet,
                has_paa=kw.has_paa,
                serp_analyzed=kw.serp_analyzed,
            )
            for kw in result.keywords
        ],
        clusters=[
            ClusterResponse(name=c.name, keywords=c.keywords, count=c.count)
            for c in result.clusters
        ],
        statistics=StatisticsResponse(
            total=result.statistics.total,
            avg_score=result.statistics.avg_score,
            intent_breakdown=result.statistics.intent_breakdown,
            source_breakdown=result.statistics.source_breakdown,
            duplicate_count=result.statistics.duplicate_count,
        ),
        processing_time_seconds=result.processing_time_seconds,
    )


# =============================================================================
# Run with: uvicorn api:app --reload --port 8001
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
