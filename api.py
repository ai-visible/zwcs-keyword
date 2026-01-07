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

from run_pipeline import run_pipeline

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
        examples=["Stripe"],
    )
    company_url: Optional[HttpUrl] = Field(
        default=None,
        description="Company website URL for deep analysis",
        examples=["https://stripe.com"],
    )
    target_count: int = Field(
        default=50,
        ge=10,
        le=500,
        description="Target number of keywords to generate",
    )
    language: str = Field(
        default="en",
        min_length=2,
        max_length=5,
        description="Target language code",
    )
    region: str = Field(
        default="us",
        min_length=2,
        max_length=5,
        description="Target region/market code",
    )
    enable_research: bool = Field(
        default=False,
        description="Enable deep research (Reddit, Quora, forums)",
    )
    min_score: int = Field(
        default=40,
        ge=0,
        le=100,
        description="Minimum company-fit score",
    )
    cluster_count: int = Field(
        default=6,
        ge=2,
        le=20,
        description="Number of keyword clusters to create",
    )

    @field_validator("company_name")
    @classmethod
    def validate_company_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Company name cannot be empty")
        return v.strip()


class KeywordResult(BaseModel):
    """Individual keyword in results."""

    keyword: str
    intent: str
    score: int
    cluster_name: Optional[str] = None
    is_question: bool = False
    source: str = "ai_generated"


class ClusterResult(BaseModel):
    """Keyword cluster in results."""

    name: str
    keywords: List[str]
    count: int


class StatisticsResult(BaseModel):
    """Statistics about generated keywords."""

    total: int
    avg_score: float
    intent_breakdown: Dict[str, int] = {}
    source_breakdown: Dict[str, int] = {}


class GenerationResponse(BaseModel):
    """Response model for keyword generation."""

    keywords: List[KeywordResult]
    clusters: List[ClusterResult]
    statistics: StatisticsResult
    processing_time_seconds: float


class JobResponse(BaseModel):
    """Response model for job status."""

    job_id: str
    status: JobStatus
    created_at: str
    completed_at: Optional[str] = None
    progress: Optional[Dict[str, Any]] = None
    result: Optional[GenerationResponse] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str = "2.0.0"
    gemini_configured: bool = False
    timestamp: str


# =============================================================================
# Job Store (In-Memory)
# =============================================================================


class JobStore:
    """Thread-safe in-memory job store."""

    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create(self, job_id: str, request: KeywordRequest) -> Dict[str, Any]:
        job = {
            "job_id": job_id,
            "status": JobStatus.PENDING,
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "request": request.model_dump(),
            "progress": None,
            "result": None,
            "error": None,
        }
        with self._lock:
            self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **kwargs) -> bool:
        with self._lock:
            if job_id not in self._jobs:
                return False
            self._jobs[job_id].update(kwargs)
            return True

    def delete(self, job_id: str) -> bool:
        with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
                return True
            return False

    def list_all(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._jobs.values())

    def cleanup_old_jobs(self, max_age_hours: int = 24, max_jobs: int = 1000) -> int:
        """Remove old jobs to prevent memory leak."""
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        removed = 0

        with self._lock:
            old_jobs = [
                job_id for job_id, job in self._jobs.items()
                if datetime.fromisoformat(job["created_at"]) < cutoff
            ]
            for job_id in old_jobs:
                del self._jobs[job_id]
                removed += 1

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
    """Validate job_id is a valid UUID."""
    try:
        uuid.UUID(job_id)
        return job_id
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job_id format (must be UUID)")


def _sanitize_csv_value(value: Any) -> str:
    """Sanitize value for CSV to prevent formula injection."""
    str_val = str(value)
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
    description="AI-powered SEO keyword generation using 5-stage pipeline",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# =============================================================================
# Health Endpoints
# =============================================================================


@app.get("/", response_model=HealthResponse, tags=["Health"])
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Check API health status."""
    return HealthResponse(
        status="healthy",
        version="2.0.0",
        gemini_configured=bool(os.getenv("GEMINI_API_KEY")),
        timestamp=datetime.utcnow().isoformat(),
    )


# =============================================================================
# Job Endpoints
# =============================================================================


@app.post(
    "/api/v1/jobs",
    response_model=JobResponse,
    status_code=201,
    tags=["Jobs"],
    summary="Create keyword generation job",
)
async def create_job(request: KeywordRequest, background_tasks: BackgroundTasks):
    """
    Create a new keyword generation job.

    The job runs asynchronously in the background. Poll GET /api/v1/jobs/{job_id}
    to check status and retrieve results when completed.
    """
    if not os.getenv("GEMINI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY not configured. Set environment variable.",
        )

    job_id = str(uuid.uuid4())
    job = job_store.create(job_id, request)

    background_tasks.add_task(_run_generation_job, job_id, request)

    return JobResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        created_at=job["created_at"],
    )


async def _run_generation_job(job_id: str, request: KeywordRequest):
    """Background task to run keyword generation."""
    try:
        job_store.update(job_id, status=JobStatus.RUNNING)

        # Run the new pipeline
        result = await run_pipeline(
            company_url=str(request.company_url) if request.company_url else f"https://{request.company_name.lower().replace(' ', '')}.com",
            company_name=request.company_name,
            target_count=request.target_count,
            language=request.language,
            region=request.region,
            enable_research=request.enable_research,
            enable_clustering=True,
            min_score=request.min_score,
            cluster_count=request.cluster_count,
        )

        # Convert pipeline result to API response format
        keywords = [
            KeywordResult(
                keyword=kw.get("keyword", ""),
                intent=kw.get("intent", "informational"),
                score=kw.get("score", 0),
                cluster_name=kw.get("cluster_name"),
                is_question=kw.get("is_question", False),
                source=kw.get("source", "ai_generated"),
            )
            for kw in result.get("keywords", [])
        ]

        clusters = [
            ClusterResult(
                name=c.get("name", ""),
                keywords=c.get("keywords", []),
                count=len(c.get("keywords", [])),
            )
            for c in result.get("clusters", [])
        ]

        # Calculate statistics
        intent_breakdown = {}
        source_breakdown = {}
        for kw in keywords:
            intent_breakdown[kw.intent] = intent_breakdown.get(kw.intent, 0) + 1
            source_breakdown[kw.source] = source_breakdown.get(kw.source, 0) + 1

        response = GenerationResponse(
            keywords=keywords,
            clusters=clusters,
            statistics=StatisticsResult(
                total=len(keywords),
                avg_score=result.get("statistics", {}).get("avg_score", 0),
                intent_breakdown=intent_breakdown,
                source_breakdown=source_breakdown,
            ),
            processing_time_seconds=result.get("statistics", {}).get("duration_seconds", 0),
        )

        job_store.update(
            job_id,
            status=JobStatus.COMPLETED,
            completed_at=datetime.utcnow().isoformat(),
            result=response.model_dump(),
            progress={"keywords_generated": len(keywords), "target_count": request.target_count},
        )

    except Exception as e:
        job_store.update(
            job_id,
            status=JobStatus.FAILED,
            completed_at=datetime.utcnow().isoformat(),
            error=str(e),
        )


@app.get(
    "/api/v1/jobs",
    response_model=List[JobResponse],
    tags=["Jobs"],
    summary="List all jobs",
)
async def list_jobs():
    """List all keyword generation jobs."""
    jobs = job_store.list_all()
    return [
        JobResponse(
            job_id=j["job_id"],
            status=j["status"],
            created_at=j["created_at"],
            completed_at=j.get("completed_at"),
            progress=j.get("progress"),
            error=j.get("error"),
        )
        for j in jobs
    ]


@app.get(
    "/api/v1/jobs/{job_id}",
    response_model=JobResponse,
    tags=["Jobs"],
    summary="Get job status",
)
async def get_job(job_id: str = Path(..., description="Job UUID")):
    """Get the status and result of a keyword generation job."""
    _validate_job_id(job_id)
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return JobResponse(
        job_id=job["job_id"],
        status=job["status"],
        created_at=job["created_at"],
        completed_at=job.get("completed_at"),
        progress=job.get("progress"),
        result=job.get("result"),
        error=job.get("error"),
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


# =============================================================================
# Export Endpoints
# =============================================================================


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
        content=job["result"],
        headers={"Content-Disposition": f"attachment; filename=keywords_{job_id}.json"},
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

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    headers = ["keyword", "intent", "score", "cluster_name", "is_question", "source"]
    writer.writerow(headers)

    # Data (sanitized to prevent CSV formula injection)
    for kw in job["result"]["keywords"]:
        writer.writerow([
            _sanitize_csv_value(kw.get("keyword", "")),
            _sanitize_csv_value(kw.get("intent", "")),
            kw.get("score", 0),
            _sanitize_csv_value(kw.get("cluster_name", "")),
            kw.get("is_question", False),
            _sanitize_csv_value(kw.get("source", "")),
        ])

    csv_content = output.getvalue()
    output.close()

    return JSONResponse(
        content={"csv": csv_content},
        headers={"Content-Disposition": f"attachment; filename=keywords_{job_id}.csv"},
    )


# =============================================================================
# Sync Generation Endpoint (for small requests)
# =============================================================================


@app.post(
    "/api/v1/generate",
    response_model=GenerationResponse,
    tags=["Generate"],
    summary="Generate keywords (sync)",
)
async def generate_sync(request: KeywordRequest):
    """
    Generate keywords synchronously.

    For small requests (≤100 keywords). Use /api/v1/jobs for larger requests.
    """
    if not os.getenv("GEMINI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY not configured. Set environment variable.",
        )

    if request.target_count > 100:
        raise HTTPException(
            status_code=400,
            detail="Use /api/v1/jobs for requests > 100 keywords",
        )

    try:
        result = await run_pipeline(
            company_url=str(request.company_url) if request.company_url else f"https://{request.company_name.lower().replace(' ', '')}.com",
            company_name=request.company_name,
            target_count=request.target_count,
            language=request.language,
            region=request.region,
            enable_research=request.enable_research,
            enable_clustering=True,
            min_score=request.min_score,
            cluster_count=request.cluster_count,
        )

        keywords = [
            KeywordResult(
                keyword=kw.get("keyword", ""),
                intent=kw.get("intent", "informational"),
                score=kw.get("score", 0),
                cluster_name=kw.get("cluster_name"),
                is_question=kw.get("is_question", False),
                source=kw.get("source", "ai_generated"),
            )
            for kw in result.get("keywords", [])
        ]

        clusters = [
            ClusterResult(
                name=c.get("name", ""),
                keywords=c.get("keywords", []),
                count=len(c.get("keywords", [])),
            )
            for c in result.get("clusters", [])
        ]

        intent_breakdown = {}
        source_breakdown = {}
        for kw in keywords:
            intent_breakdown[kw.intent] = intent_breakdown.get(kw.intent, 0) + 1
            source_breakdown[kw.source] = source_breakdown.get(kw.source, 0) + 1

        return GenerationResponse(
            keywords=keywords,
            clusters=clusters,
            statistics=StatisticsResult(
                total=len(keywords),
                avg_score=result.get("statistics", {}).get("avg_score", 0),
                intent_breakdown=intent_breakdown,
                source_breakdown=source_breakdown,
            ),
            processing_time_seconds=result.get("statistics", {}).get("duration_seconds", 0),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
