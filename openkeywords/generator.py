"""
Core keyword generation using Google Gemini
"""

import asyncio
import json
import logging
import os
import time
from collections import defaultdict
from typing import Optional

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential

from .models import (
    Cluster,
    CompanyInfo,
    GenerationConfig,
    GenerationResult,
    Keyword,
    KeywordStatistics,
)

logger = logging.getLogger(__name__)

# Valid intent types
VALID_INTENTS = {"transactional", "commercial", "comparison", "informational", "question"}

# Question starters by language
QUESTION_STARTERS = {
    "de": ["wie", "was", "warum", "wann", "wo", "welch", "wer", "woher", "wohin", "weshalb"],
    "en": ["how", "what", "why", "when", "where", "which", "who", "can", "should", "is", "are"],
    "fr": ["comment", "quoi", "pourquoi", "quand", "où", "quel", "qui"],
    "es": ["cómo", "qué", "por qué", "cuándo", "dónde", "cuál", "quién"],
    "it": ["come", "cosa", "perché", "quando", "dove", "quale", "chi"],
    "nl": ["hoe", "wat", "waarom", "wanneer", "waar", "welke", "wie"],
}

# Intent detection patterns by language
INTENT_PATTERNS = {
    "de": {
        "comparison": ["vs", "versus", "alternative", "unterschied", "vergleich", "oder"],
        "transactional": ["buchen", "kaufen", "bestellen", "termin", "anfragen", "vereinbaren"],
        "commercial": ["beste", "bester", "top", "kosten", "preis", "bewertung", "erfahrungen"],
    },
    "en": {
        "comparison": ["vs", "versus", "alternative", "difference", "compared", "comparison"],
        "transactional": ["book", "buy", "purchase", "order", "get", "hire", "sign up"],
        "commercial": ["best", "top", "review", "pricing", "cost", "price", "rated", "compare"],
    },
    "default": {
        "comparison": ["vs", "versus", "alternative", "difference", "compared"],
        "transactional": ["book", "buy", "purchase", "order", "get"],
        "commercial": ["best", "top", "review", "pricing", "cost"],
    },
}


class KeywordGenerator:
    """
    AI-powered keyword generator using Google Gemini.

    Features:
    - Diverse keyword generation (question, commercial, transactional, etc.)
    - Company-fit scoring
    - Semantic clustering
    - Intelligent deduplication
    - Optional SE Ranking volume data
    """

    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        seranking_api_key: Optional[str] = None,
        model: str = "gemini-1.5-flash",
    ):
        """
        Initialize the keyword generator.

        Args:
            gemini_api_key: Google Gemini API key (or set GEMINI_API_KEY env var)
            seranking_api_key: SE Ranking API key (optional, for volume data)
            model: Gemini model to use (default: gemini-1.5-flash)
        """
        self.api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Gemini API key required. Set GEMINI_API_KEY env var or pass gemini_api_key."
            )

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model)
        self.model_name = model

        # SE Ranking client (optional)
        self.seranking_api_key = seranking_api_key or os.getenv("SERANKING_API_KEY")
        self.seranking_client = None

        if self.seranking_api_key:
            try:
                from .seranking import SERankingClient

                self.seranking_client = SERankingClient(self.seranking_api_key)
                logger.info("SE Ranking client initialized")
            except Exception as e:
                logger.warning(f"SE Ranking client initialization failed: {e}")

    async def generate(
        self,
        company_info: CompanyInfo,
        config: Optional[GenerationConfig] = None,
    ) -> GenerationResult:
        """
        Generate keywords for a company.

        Args:
            company_info: Company information
            config: Generation configuration

        Returns:
            GenerationResult with keywords, clusters, and statistics
        """
        start_time = time.time()
        config = config or GenerationConfig()

        logger.info(f"Generating {config.target_count} keywords for {company_info.name}")

        # Step 1: Generate raw keywords
        keywords = await self._generate_keywords(company_info, config)
        logger.info(f"Generated {len(keywords)} raw keywords")

        if not keywords:
            return GenerationResult(
                keywords=[],
                clusters=[],
                statistics=KeywordStatistics(total=0),
                processing_time_seconds=time.time() - start_time,
            )

        # Step 2: Deduplicate
        keywords, dup_count = self._deduplicate(keywords)
        logger.info(f"After dedup: {len(keywords)} keywords ({dup_count} removed)")

        # Step 3: Score keywords
        keywords = await self._score_keywords(keywords, company_info)
        logger.info(f"Scored {len(keywords)} keywords")

        # Step 4: Filter by score
        keywords = [kw for kw in keywords if kw.get("score", 0) >= config.min_score]
        logger.info(f"After score filter: {len(keywords)} keywords")

        # Step 5: Fetch SE Ranking volume (optional)
        if config.enable_volume and self.seranking_client:
            keywords = await self._fetch_volume_data(keywords, config)

        # Step 6: Cluster keywords
        if config.enable_clustering and len(keywords) > 0:
            keywords = await self._cluster_keywords(keywords, company_info, config.cluster_count)

        # Step 7: Limit to target count
        keywords = keywords[: config.target_count]

        # Build result
        keyword_objects = [
            Keyword(
                keyword=kw["keyword"],
                intent=kw.get("intent", "informational"),
                score=kw.get("score", 0),
                cluster_name=kw.get("cluster_name"),
                is_question=kw.get("is_question", False),
                volume=kw.get("volume", 0),
                difficulty=kw.get("difficulty", 50),
            )
            for kw in keywords
        ]

        # Build clusters
        clusters_map = defaultdict(list)
        for kw in keyword_objects:
            if kw.cluster_name:
                clusters_map[kw.cluster_name].append(kw.keyword)

        clusters = [Cluster(name=name, keywords=kws) for name, kws in clusters_map.items()]

        # Calculate statistics
        stats = self._calculate_statistics(keyword_objects, dup_count)

        processing_time = time.time() - start_time
        logger.info(f"Generation complete: {len(keyword_objects)} keywords in {processing_time:.1f}s")

        return GenerationResult(
            keywords=keyword_objects,
            clusters=clusters,
            statistics=stats,
            processing_time_seconds=processing_time,
        )

    async def _generate_keywords(
        self, company_info: CompanyInfo, config: GenerationConfig
    ) -> list[dict]:
        """Generate keywords using Gemini in parallel batches."""
        # Build company context
        context_parts = [f"Company: {company_info.name}"]
        if company_info.industry:
            context_parts.append(f"Industry: {company_info.industry}")
        if company_info.description:
            context_parts.append(f"Description: {company_info.description}")
        if company_info.services:
            context_parts.append(f"Services: {', '.join(company_info.services)}")
        if company_info.products:
            context_parts.append(f"Products: {', '.join(company_info.products)}")
        if company_info.brands:
            context_parts.append(f"Brands: {', '.join(company_info.brands)}")
        if company_info.target_location:
            context_parts.append(f"Location: {company_info.target_location}")
        if company_info.target_audience:
            context_parts.append(f"Target Audience: {company_info.target_audience}")

        company_context = "\n".join(context_parts)

        # Over-generate to account for deduplication and filtering
        buffer_count = int(config.target_count * 2.5)
        batch_size = 15
        num_batches = (buffer_count + batch_size - 1) // batch_size

        logger.info(f"Generating {buffer_count} keywords in {num_batches} batches")

        # Generate batches in parallel
        tasks = [
            self._generate_batch(
                company_context, batch_size, i + 1, num_batches, config.language, config.region
            )
            for i in range(num_batches)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_keywords = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Batch failed: {result}")
            elif result:
                all_keywords.extend(result)

        return all_keywords

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _generate_batch(
        self,
        company_context: str,
        batch_count: int,
        batch_num: int,
        total_batches: int,
        language: str,
        region: str,
    ) -> list[dict]:
        """Generate a single batch of keywords."""
        lang_code = language.lower()[:2] if language else "en"
        lang_upper = language.upper()
        region_upper = region.upper()

        # Calculate minimum counts per intent type
        question_min = max(3, int(batch_count * 0.25))
        commercial_min = max(3, int(batch_count * 0.25))
        transactional_min = max(2, int(batch_count * 0.15))
        comparison_min = max(1, int(batch_count * 0.10))

        prompt = f"""Generate {batch_count} SEO keywords in {lang_upper} for {region_upper} market.

{company_context}

INTENT TYPES (strict counts):
- {question_min}+ QUESTION: start with how/what/why/when/where/which
- {transactional_min}+ TRANSACTIONAL: book, buy, order, get quote, sign up
- {comparison_min}+ COMPARISON: vs, alternative, difference, compared to
- {commercial_min}+ COMMERCIAL: best, top, review, pricing, cost
- Rest INFORMATIONAL (max 25%): guides, benefits, tips

KEYWORD LENGTH:
- 20% SHORT keywords (2-3 words)
- 50% MEDIUM keywords (4-5 words)
- 30% LONG keywords (6-7 words)

RULES:
- NO single-word keywords
- NO keywords longer than 7 words
- Be specific to company offerings
- Include location terms ({region_upper})

Return JSON: {{"keywords": [{{"keyword": "...", "intent": "question|transactional|comparison|commercial|informational", "is_question": true/false}}]}}"""

        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.8,
                    response_mime_type="application/json",
                ),
            )

            data = self._parse_json_response(response.text)
            keywords_data = data.get("keywords", [])

            if not keywords_data:
                logger.warning(f"Batch {batch_num}: No keywords returned")
                return []

            # Process and validate keywords
            processed = []
            question_words = QUESTION_STARTERS.get(lang_code, QUESTION_STARTERS["en"])

            for kw in keywords_data:
                keyword_text = kw.get("keyword", "").strip()
                if not keyword_text:
                    continue

                # Validate and classify intent
                validated_intent = self._classify_intent(
                    keyword_text, kw.get("intent", ""), lang_code
                )

                # Auto-detect questions
                is_question = kw.get("is_question", False)
                if not is_question:
                    kw_lower = keyword_text.lower()
                    is_question = any(kw_lower.startswith(q) for q in question_words)

                if is_question and validated_intent != "question":
                    validated_intent = "question"

                processed.append(
                    {
                        "keyword": keyword_text,
                        "intent": validated_intent,
                        "is_question": is_question,
                        "score": 0,
                    }
                )

            logger.info(f"Batch {batch_num}/{total_batches}: {len(processed)} keywords")
            return processed

        except Exception as e:
            logger.error(f"Batch {batch_num} failed: {e}")
            raise

    def _classify_intent(self, keyword: str, ai_intent: str, lang_code: str) -> str:
        """Validate and classify keyword intent."""
        # Use AI intent if valid
        if ai_intent and ai_intent.lower() in VALID_INTENTS:
            return ai_intent.lower()

        # Get language-specific patterns
        patterns = INTENT_PATTERNS.get(lang_code, INTENT_PATTERNS["default"])
        question_words = QUESTION_STARTERS.get(lang_code, QUESTION_STARTERS["en"])

        kw_lower = keyword.lower()

        # Check question patterns
        if any(kw_lower.startswith(q) for q in question_words):
            return "question"

        # Check comparison patterns
        if any(pattern in kw_lower for pattern in patterns["comparison"]):
            return "comparison"

        # Check transactional patterns
        if any(pattern in kw_lower for pattern in patterns["transactional"]):
            return "transactional"

        # Check commercial patterns
        if any(pattern in kw_lower for pattern in patterns["commercial"]):
            return "commercial"

        return "informational"

    def _deduplicate(self, keywords: list[dict]) -> tuple[list[dict], int]:
        """Remove exact and near-duplicate keywords using O(n) token signature grouping."""
        if not keywords:
            return [], 0

        original_count = len(keywords)

        # Phase 1: Exact match removal
        seen_exact = set()
        phase1 = []
        for kw in keywords:
            normalized = kw.get("keyword", "").lower().strip()
            if not normalized:
                continue
            if normalized not in seen_exact:
                seen_exact.add(normalized)
                phase1.append(kw)

        # Phase 2: Token signature grouping
        groups = defaultdict(list)
        for kw in phase1:
            keyword_text = kw.get("keyword", "").lower().strip()
            tokens = tuple(sorted(keyword_text.split()))
            groups[tokens].append(kw)

        # Keep highest scored keyword from each group
        unique = []
        for token_group in groups.values():
            if len(token_group) == 1:
                unique.append(token_group[0])
            else:
                best = max(token_group, key=lambda x: x.get("score", 0))
                unique.append(best)

        duplicate_count = original_count - len(unique)
        return unique, duplicate_count

    async def _score_keywords(
        self, keywords: list[dict], company_info: CompanyInfo
    ) -> list[dict]:
        """Score keywords for company fit using Gemini."""
        if not keywords:
            return []

        # Build company context
        context_parts = [f"Company: {company_info.name}"]
        if company_info.description:
            context_parts.append(f"Description: {company_info.description}")
        if company_info.services:
            context_parts.append(f"Services: {', '.join(company_info.services)}")
        if company_info.products:
            context_parts.append(f"Products: {', '.join(company_info.products)}")

        company_context = "\n".join(context_parts)

        # Score in batches
        batch_size = 25
        num_batches = (len(keywords) + batch_size - 1) // batch_size

        tasks = [
            self._score_batch(
                keywords[i * batch_size : (i + 1) * batch_size], company_context, i + 1, num_batches
            )
            for i in range(num_batches)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_scored = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Scoring batch {i + 1} failed: {result}")
                # Keep keywords with default score
                batch = keywords[i * batch_size : (i + 1) * batch_size]
                for kw in batch:
                    kw["score"] = 50
                all_scored.extend(batch)
            elif result:
                all_scored.extend(result)

        # Sort by score
        all_scored.sort(key=lambda x: x.get("score", 0), reverse=True)
        return all_scored

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _score_batch(
        self,
        keywords: list[dict],
        company_context: str,
        batch_num: int,
        total_batches: int,
    ) -> list[dict]:
        """Score a batch of keywords."""
        keywords_text = "\n".join([f"- {kw['keyword']}" for kw in keywords])

        prompt = f"""Score these keywords for company fit on a 1-100 scale.

{company_context}

Keywords to score:
{keywords_text}

Scoring criteria:
- Product/Service relevance (0-40 points)
- Search intent match (0-30 points)
- Business value potential (0-30 points)

Return ONLY a JSON object:
{{"scores": [{{"keyword": "exact keyword", "score": 75}}]}}"""

        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    response_mime_type="application/json",
                ),
            )

            data = self._parse_json_response(response.text)
            scores_data = data.get("scores", [])

            if isinstance(scores_data, list):
                score_map = {item["keyword"]: item.get("score", 50) for item in scores_data}

                scored = []
                for kw in keywords:
                    kw_copy = dict(kw)
                    kw_copy["score"] = score_map.get(kw["keyword"], 50)
                    scored.append(kw_copy)

                logger.info(f"Scoring batch {batch_num}/{total_batches}: {len(scored)} keywords")
                return scored

        except Exception as e:
            logger.error(f"Scoring batch {batch_num} failed: {e}")
            raise

        return keywords

    async def _cluster_keywords(
        self, keywords: list[dict], company_info: CompanyInfo, cluster_count: int
    ) -> list[dict]:
        """Cluster keywords into semantic groups using Gemini."""
        if not keywords:
            return []

        keywords_text = "\n".join([f"- {kw['keyword']}" for kw in keywords])

        prompt = f"""Group these keywords into {cluster_count} semantic clusters for {company_info.name}.

Keywords:
{keywords_text}

Requirements:
- Create exactly {cluster_count} clusters
- Each cluster should have a descriptive name (2-4 words)
- Group keywords by theme/topic
- Each keyword should belong to exactly one cluster

Return ONLY a JSON object:
{{"clusters": [
  {{"cluster_name": "Product Features", "keywords": ["keyword1", "keyword2"]}},
  {{"cluster_name": "How-To Guides", "keywords": ["keyword3", "keyword4"]}}
]}}"""

        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.5,
                    response_mime_type="application/json",
                ),
            )

            data = self._parse_json_response(response.text)
            clusters_data = data.get("clusters", [])

            if isinstance(clusters_data, list):
                # Map cluster names to keywords
                cluster_map = {}
                for cluster in clusters_data:
                    cluster_name = cluster.get("cluster_name", "Uncategorized")
                    for kw_text in cluster.get("keywords", []):
                        cluster_map[kw_text.lower().strip()] = cluster_name

                # Apply cluster names
                for kw in keywords:
                    kw_text = kw["keyword"].lower().strip()
                    kw["cluster_name"] = cluster_map.get(kw_text, "Other")

                logger.info(f"Clustered {len(keywords)} keywords into {len(clusters_data)} groups")

        except Exception as e:
            logger.error(f"Clustering failed: {e}")
            for kw in keywords:
                kw["cluster_name"] = "General"

        return keywords

    async def _fetch_volume_data(
        self, keywords: list[dict], config: GenerationConfig
    ) -> list[dict]:
        """Fetch volume and difficulty data from SE Ranking."""
        if not self.seranking_client:
            return keywords

        try:
            keyword_texts = [kw["keyword"] for kw in keywords]
            volume_data = await self.seranking_client.get_volume_batch(
                keyword_texts, config.region
            )

            # Apply volume data
            for kw in keywords:
                kw_data = volume_data.get(kw["keyword"].lower(), {})
                kw["volume"] = kw_data.get("volume", 0)
                kw["difficulty"] = kw_data.get("difficulty", 50)

            logger.info(f"Fetched volume data for {len(keywords)} keywords")

        except Exception as e:
            logger.error(f"SE Ranking volume fetch failed: {e}")

        return keywords

    def _parse_json_response(self, response_text: str) -> dict:
        """Parse JSON from AI response, handling markdown code blocks."""
        try:
            text = response_text.strip()

            # Handle markdown code blocks
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            return json.loads(text)
        except (json.JSONDecodeError, IndexError) as e:
            logger.error(f"JSON parse error: {e}. Response: {response_text[:200]}")
            return {"keywords": []}

    def _calculate_statistics(
        self, keywords: list[Keyword], duplicate_count: int
    ) -> KeywordStatistics:
        """Calculate statistics for generated keywords."""
        if not keywords:
            return KeywordStatistics(total=0, duplicate_count=duplicate_count)

        intent_counts = defaultdict(int)
        length_counts = {"short": 0, "medium": 0, "long": 0}

        for kw in keywords:
            intent_counts[kw.intent] += 1

            word_count = len(kw.keyword.split())
            if word_count <= 3:
                length_counts["short"] += 1
            elif word_count <= 5:
                length_counts["medium"] += 1
            else:
                length_counts["long"] += 1

        return KeywordStatistics(
            total=len(keywords),
            avg_score=sum(kw.score for kw in keywords) / len(keywords),
            intent_breakdown=dict(intent_counts),
            word_length_distribution=length_counts,
            duplicate_count=duplicate_count,
        )

