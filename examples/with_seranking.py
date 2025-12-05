"""
OpenKeywords - Example with SE Ranking Volume Data

Before running, set your API keys:
    export GEMINI_API_KEY='your-gemini-api-key'
    export SERANKING_API_KEY='your-seranking-api-key'
"""

import asyncio
import os

from openkeywords import KeywordGenerator, CompanyInfo, GenerationConfig


async def main():
    # Check API keys
    if not os.getenv("GEMINI_API_KEY"):
        print("Error: Set GEMINI_API_KEY environment variable")
        return

    if not os.getenv("SERANKING_API_KEY"):
        print("Warning: SERANKING_API_KEY not set - volume data will be skipped")
        enable_volume = False
    else:
        enable_volume = True

    # Initialize generator with SE Ranking
    generator = KeywordGenerator()

    # Define company
    company = CompanyInfo(
        name="FitnessPro",
        url="https://fitnesspro.example.com",
        industry="Health & Fitness",
        description="Online fitness coaching and workout programs",
        services=["personal training", "nutrition coaching", "workout plans"],
        products=["FitnessPro App", "Meal Plans"],
        target_audience="health-conscious adults",
        target_location="United States",
        competitors=["competitor1.com", "competitor2.com"],
    )

    # Configure with SE Ranking volume
    config = GenerationConfig(
        target_count=50,
        min_score=45,
        enable_clustering=True,
        cluster_count=6,
        language="english",
        region="us",
        enable_volume=enable_volume,  # Fetch real search volume
    )

    print(f"\n🔑 Generating keywords for {company.name}...")
    print(f"   SE Ranking volume: {'enabled' if enable_volume else 'disabled'}\n")

    # Generate keywords
    result = await generator.generate(company, config)

    print(f"✓ Generated {len(result.keywords)} keywords in {result.processing_time_seconds:.1f}s")

    # Display with volume data
    print("\n📝 Top Keywords with Volume:")
    print("-" * 90)
    print(f"{'Keyword':<40} | {'Intent':<12} | {'Score':>5} | {'Volume':>7} | {'Diff':>4}")
    print("-" * 90)

    for kw in result.keywords[:15]:
        print(
            f"{kw.keyword:<40} | {kw.intent:<12} | {kw.score:>5} | {kw.volume:>7} | {kw.difficulty:>4}"
        )

    # Sort by volume (if available)
    if enable_volume:
        by_volume = sorted(result.keywords, key=lambda x: x.volume, reverse=True)
        print("\n📈 Top 10 by Search Volume:")
        print("-" * 70)
        for kw in by_volume[:10]:
            print(f"  {kw.keyword:<40} | Volume: {kw.volume:>6}")

    # Export
    result.to_csv("keywords_with_volume.csv")
    print("\n✓ Exported to keywords_with_volume.csv")


if __name__ == "__main__":
    asyncio.run(main())

