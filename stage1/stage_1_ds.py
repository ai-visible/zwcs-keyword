"""
Stage 1: Company Analysis (DeepSeek Version)

Analyzes company website using OpenAI-compatible client (DeepSeek).
Extracts rich context for hyper-specific keyword generation.
"""

import asyncio
import json
import logging
import os
from typing import Optional

from openai import OpenAI

from .stage1_models import Stage1Input, Stage1Output, CompanyContext

logger = logging.getLogger(__name__)

# Response schema for structured company analysis
COMPANY_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "company_name": {"type": "string"},
        "description": {"type": "string"},
        "industry": {"type": "string"},
        "target_audience": {"type": "array", "items": {"type": "string"}},
        "products": {"type": "array", "items": {"type": "string"}},
        "services": {"type": "array", "items": {"type": "string"}},
        "pain_points": {"type": "array", "items": {"type": "string"}},
        "customer_problems": {"type": "array", "items": {"type": "string"}},
        "use_cases": {"type": "array", "items": {"type": "string"}},
        "value_propositions": {"type": "array", "items": {"type": "string"}},
        "differentiators": {"type": "array", "items": {"type": "string"}},
        "key_features": {"type": "array", "items": {"type": "string"}},
        "solution_keywords": {"type": "array", "items": {"type": "string"}},
        "competitors": {"type": "array", "items": {"type": "string"}},
        "brand_voice": {"type": "string"},
        "product_category": {"type": "string"},
        "primary_region": {"type": "string"},
    },
    "required": ["company_name", "description", "industry", "products"],
}


async def run_stage_1(input_data: Stage1Input) -> Stage1Output:
    """
    Run Stage 1: Company Analysis

    Args:
        input_data: Stage1Input with company URL and optional overrides

    Returns:
        Stage1Output with rich company context
    """
    logger.info("=" * 60)
    logger.info("[Stage 1] Company Analysis (DeepSeek)")
    logger.info("=" * 60)
    logger.info(f"  URL: {input_data.company_url}")

    # Initialize OpenAI client
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY environment variable required")

    base_url = "https://api.deepseek.com"
    client = OpenAI(api_key=api_key, base_url=base_url)

    # Get current date for context
    from datetime import datetime
    current_date = datetime.now().strftime("%B %Y")

    # Build analysis prompt
    prompt = f"""Today's date: {current_date}

You are an expert business analyst, content strategist, and visual designer. Analyze the company website at {input_data.company_url} and extract comprehensive company context INCLUDING a detailed writing persona AND visual identity for image generation.

IMPORTANT INSTRUCTIONS:
1. Use the URL Context tool to fetch and analyze the actual content at {input_data.company_url}
2. Use Google Search to find additional real information about this company
3. Do NOT make up or hallucinate data - only use information you actually retrieve
4. If you cannot find information about the company, return an error field in the JSON
5. **CRITICAL: Find and analyze existing blog post images for visual style reference**

Analyze all retrieved information to provide:

1. COMPANY BASICS
   - Company name (official name)
   - Description (2-3 sentences about what they do)
   - Industry (be specific: EdTech, FinTech, B2B SaaS, etc.)

2. PRODUCTS & SERVICES
   - What do they SELL? (use actual product/service names)
   - What services do they offer?

3. CUSTOMER INSIGHTS
   - Who are their customers? (include company sizes: startups, SMEs, enterprise)
   - What pain points do customers have?
   - What problems does their solution solve?
   - Real use cases where the product is used

4. VALUE & DIFFERENTIATION
   - Key value propositions
   - What makes them unique vs competitors?
   - Key features and capabilities
   - Terms describing their approach/solution

5. MARKET
   - Who are their main competitors? (3-5 names)
   - Primary geographic region (US, Europe, Global, etc.)

6. BRAND
   - Brand voice (formal/casual, technical/simple)
   - Product category

Be thorough and specific. Use real information from search results.

Return JSON matching this schema:
{json.dumps(COMPANY_ANALYSIS_SCHEMA, indent=2)}"""

    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="deepseek-reasoner",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that analyzes companies and returns valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            response_format={"type": "json_object"},
            extra_body={
                "web_search": True,
                "thinking": {"type": "enabled"},
            },
        )

        response_content = response.choices[0].message.content
        if not response_content:
            raise ValueError("Empty response from DeepSeek")

        # Handle markdown code blocks if present
        response_text = response_content.strip()
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        analysis = json.loads(response_text)

        # Override company name if provided
        if input_data.company_name:
            analysis["company_name"] = input_data.company_name

        # Build CompanyContext from analysis
        company_context = CompanyContext(
            company_name=analysis.get("company_name", "Unknown"),
            company_url=input_data.company_url,
            description=analysis.get("description"),
            industry=analysis.get("industry"),
            products=analysis.get("products", []),
            services=analysis.get("services", []),
            target_audience=analysis.get("target_audience", []),
            pain_points=analysis.get("pain_points", []),
            customer_problems=analysis.get("customer_problems", []),
            use_cases=analysis.get("use_cases", []),
            value_propositions=analysis.get("value_propositions", []),
            differentiators=analysis.get("differentiators", []),
            key_features=analysis.get("key_features", []),
            solution_keywords=analysis.get("solution_keywords", []),
            competitors=analysis.get("competitors", []),
            primary_region=analysis.get("primary_region"),
            brand_voice=analysis.get("brand_voice"),
            product_category=analysis.get("product_category"),
        )

        logger.info(f"  ✓ Company: {company_context.company_name}")
        logger.info(f"  ✓ Industry: {company_context.industry}")
        logger.info(f"  ✓ Products: {len(company_context.products)}")
        logger.info(f"  ✓ Services: {len(company_context.services)}")
        logger.info(f"  ✓ Pain points: {len(company_context.pain_points)}")
        logger.info(f"  ✓ Competitors: {len(company_context.competitors)}")

        return Stage1Output(
            company_context=company_context,
            language=input_data.language,
            region=input_data.region,
            ai_calls=1,
        )

    except Exception as e:
        logger.error(f"Stage 1 failed: {e}")
        raise
