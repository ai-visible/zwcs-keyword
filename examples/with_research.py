"""
OpenKeywords - Deep Research Example

Deep Research uses Google Search grounding to find hyper-niche keywords
from Reddit, Quora, forums, and other community discussions.

Before running, set your API key:
    export GEMINI_API_KEY='your-gemini-api-key'

Run from project root:
    python examples/with_research.py
"""

import asyncio
import os

from openkeywords import KeywordGenerator, CompanyInfo, GenerationConfig


async def main():
    if not os.getenv("GEMINI_API_KEY"):
        print("Error: Set GEMINI_API_KEY environment variable")
        return

    generator = KeywordGenerator()

    # Define company
    company = CompanyInfo(
        name="DevOps Pro",
        industry="DevOps & Cloud Infrastructure",
        description="CI/CD pipeline and cloud deployment solutions",
        services=["CI/CD automation", "Kubernetes management", "cloud migration"],
        products=["DevOps Pro Platform", "Pipeline Builder"],
        target_audience="software development teams",
        target_location="United States",
    )

    # Enable deep research to find hyper-niche keywords
    config = GenerationConfig(
        target_count=40,
        min_score=40,
        enable_clustering=True,
        cluster_count=5,
        language="english",
        region="us",
        enable_research=True,  # 🔍 This enables Reddit, Quora, forum search
    )

    print(f"\n🔍 Deep Research Demo")
    print("=" * 60)
    print(f"Company: {company.name}")
    print(f"Industry: {company.industry}")
    print(f"Research: ENABLED (Reddit, Quora, forums)")
    print("=" * 60)

    result = await generator.generate(company, config)

    print(f"\n✓ Generated {len(result.keywords)} keywords in {result.processing_time_seconds:.1f}s")

    # Show source breakdown
    print("\n📊 Keyword Sources:")
    for source, count in result.statistics.source_breakdown.items():
        pct = (count / len(result.keywords)) * 100
        icon = "🔍" if "research" in source else "🤖"
        print(f"   {icon} {source}: {count} ({pct:.0f}%)")

    # Show research-found keywords specifically
    research_keywords = [kw for kw in result.keywords if "research" in kw.source]
    if research_keywords:
        print(f"\n🔍 Keywords from Deep Research ({len(research_keywords)}):")
        print("-" * 60)
        for kw in research_keywords[:15]:
            source_short = kw.source.replace("research_", "")
            print(f"  [{source_short}] {kw.keyword}")
            if kw.is_question:
                print(f"         ^ Question keyword - great for AEO!")

    # Show question keywords (great for AEO)
    questions = [kw for kw in result.keywords if kw.is_question or kw.intent == "question"]
    print(f"\n❓ Question Keywords ({len(questions)} - excellent for AEO):")
    print("-" * 60)
    for kw in questions[:10]:
        src = "🔍" if "research" in kw.source else "🤖"
        print(f"  {src} {kw.keyword}")

    # Export with source info
    result.to_csv("keywords_with_research.csv")
    result.to_json("keywords_with_research.json")
    print(f"\n✓ Exported to keywords_with_research.csv and .json")
    print("  (CSV includes 'source' column showing where each keyword came from)")


if __name__ == "__main__":
    asyncio.run(main())

