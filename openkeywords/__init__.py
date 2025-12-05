"""
OpenKeywords - AI-powered SEO keyword generation using Gemini + SE Ranking.

Generate high-quality, clustered SEO keywords for any business.

Usage:
    from openkeywords import KeywordGenerator, CompanyInfo

    generator = KeywordGenerator()
    result = await generator.generate(
        CompanyInfo(name="Acme Software", industry="B2B SaaS"),
    )

    for kw in result.keywords:
        print(f"{kw.keyword} | {kw.intent} | Score: {kw.score}")
"""

from .models import (
    Cluster,
    CompanyInfo,
    GenerationConfig,
    GenerationResult,
    Keyword,
    KeywordStatistics,
)
from .generator import KeywordGenerator

__version__ = "0.1.0"
__all__ = [
    "KeywordGenerator",
    "CompanyInfo",
    "GenerationConfig",
    "GenerationResult",
    "Keyword",
    "Cluster",
    "KeywordStatistics",
]

