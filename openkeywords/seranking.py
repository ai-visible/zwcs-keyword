"""
SE Ranking API client for keyword volume and difficulty data.

Optional integration - requires SE Ranking API key.
https://seranking.com/api-documentation.html
"""

import asyncio
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://api.seranking.com/v1"


class SERankingClient:
    """
    SE Ranking API client for fetching keyword volume and difficulty.

    Usage:
        client = SERankingClient("your-api-key")
        data = await client.get_volume_batch(["keyword1", "keyword2"], "us")
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize SE Ranking client.

        Args:
            api_key: SE Ranking API key (or set SERANKING_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("SERANKING_API_KEY")
        if not self.api_key:
            raise ValueError(
                "SE Ranking API key required. Set SERANKING_API_KEY env var or pass api_key."
            )

        self.base_url = BASE_URL
        self.timeout = 30.0

    async def get_volume(self, keyword: str, region: str = "us") -> dict:
        """
        Get volume and difficulty for a single keyword.

        Args:
            keyword: Keyword to look up
            region: Region code (e.g., 'us', 'de', 'uk')

        Returns:
            Dict with 'volume' and 'difficulty' keys
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/keywords/volume",
                    params={
                        "keyword": keyword,
                        "region_id": self._get_region_id(region),
                    },
                    headers={"Authorization": f"Token {self.api_key}"},
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "volume": data.get("search_volume", 0),
                        "difficulty": data.get("difficulty", 50),
                    }
                else:
                    logger.warning(f"SE Ranking API error: {response.status_code}")
                    return {"volume": 0, "difficulty": 50}

        except Exception as e:
            logger.error(f"SE Ranking request failed: {e}")
            return {"volume": 0, "difficulty": 50}

    async def get_volume_batch(
        self, keywords: list[str], region: str = "us", batch_size: int = 100
    ) -> dict[str, dict]:
        """
        Get volume and difficulty for multiple keywords.

        Args:
            keywords: List of keywords to look up
            region: Region code (e.g., 'us', 'de', 'uk')
            batch_size: Number of keywords per batch

        Returns:
            Dict mapping keyword (lowercase) to {volume, difficulty}
        """
        if not keywords:
            return {}

        results = {}
        region_id = self._get_region_id(region)

        # Process in batches
        for i in range(0, len(keywords), batch_size):
            batch = keywords[i : i + batch_size]

            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/keywords/volume/batch",
                        json={
                            "keywords": batch,
                            "region_id": region_id,
                        },
                        headers={
                            "Authorization": f"Token {self.api_key}",
                            "Content-Type": "application/json",
                        },
                    )

                    if response.status_code == 200:
                        data = response.json()
                        for item in data.get("data", []):
                            kw = item.get("keyword", "").lower()
                            results[kw] = {
                                "volume": item.get("search_volume", 0),
                                "difficulty": item.get("difficulty", 50),
                            }
                    else:
                        logger.warning(f"SE Ranking batch API error: {response.status_code}")

            except Exception as e:
                logger.error(f"SE Ranking batch request failed: {e}")

            # Rate limiting
            await asyncio.sleep(0.5)

        logger.info(f"Fetched volume for {len(results)}/{len(keywords)} keywords")
        return results

    async def analyze_competitors(
        self, domain: str, competitors: list[str], region: str = "us"
    ) -> list[dict]:
        """
        Analyze keyword gaps between domain and competitors.

        Args:
            domain: Your domain
            competitors: List of competitor domains
            region: Region code

        Returns:
            List of gap keywords with volume/difficulty
        """
        if not competitors:
            return []

        gap_keywords = []
        region_id = self._get_region_id(region)

        for competitor in competitors[:3]:  # Limit to 3 competitors
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{self.base_url}/domain/competitors/content-gap",
                        json={
                            "domain": domain,
                            "competitor": competitor,
                            "region_id": region_id,
                        },
                        headers={
                            "Authorization": f"Token {self.api_key}",
                            "Content-Type": "application/json",
                        },
                    )

                    if response.status_code == 200:
                        data = response.json()
                        for item in data.get("keywords", []):
                            gap_keywords.append(
                                {
                                    "keyword": item.get("keyword", ""),
                                    "volume": item.get("search_volume", 0),
                                    "difficulty": item.get("difficulty", 50),
                                    "source": "gap_analysis",
                                    "competitor": competitor,
                                }
                            )
                    else:
                        logger.warning(
                            f"SE Ranking gap analysis error for {competitor}: {response.status_code}"
                        )

            except Exception as e:
                logger.error(f"SE Ranking gap analysis failed for {competitor}: {e}")

            # Rate limiting
            await asyncio.sleep(1.0)

        logger.info(f"Found {len(gap_keywords)} gap keywords from {len(competitors)} competitors")
        return gap_keywords

    def _get_region_id(self, region: str) -> int:
        """Map region code to SE Ranking region ID."""
        # Common region mappings (SE Ranking uses numeric IDs)
        region_map = {
            "us": 2840,  # United States
            "uk": 2826,  # United Kingdom
            "de": 2276,  # Germany
            "fr": 2250,  # France
            "es": 2724,  # Spain
            "it": 2380,  # Italy
            "nl": 2528,  # Netherlands
            "au": 2036,  # Australia
            "ca": 2124,  # Canada
            "br": 2076,  # Brazil
            "in": 2356,  # India
            "jp": 2392,  # Japan
        }
        return region_map.get(region.lower(), 2840)  # Default to US

    async def test_connection(self) -> bool:
        """Test if API key is valid."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/account",
                    headers={"Authorization": f"Token {self.api_key}"},
                )
                if response.status_code == 200:
                    logger.info("SE Ranking API connection successful")
                    return True
                else:
                    logger.error(f"SE Ranking API error: {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"SE Ranking connection test failed: {e}")
            return False

