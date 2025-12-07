"""
Company Analysis Module for OpenKeywords

Pre-analyzes company website to extract rich context before keyword generation.
This ensures keywords are company-specific, not generic industry keywords.

Uses Gemini 3 Pro Preview with url_context + google_search for:
- Company description & industry
- Products & services (what they SELL)
- Pain points & customer problems
- Value propositions & differentiators  
- Competitors
- Target audience
- Use cases
- Brand voice & tone

This rich context feeds into the keyword generator for HYPER-SPECIFIC results.
"""

import os
import logging
from typing import Optional
import google.generativeai as genai

logger = logging.getLogger(__name__)

# Response schema for structured company analysis
COMPANY_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "company_name": {"type": "string"},
        "description": {"type": "string", "description": "2-3 sentences about what the company does"},
        "industry": {"type": "string", "description": "Industry category (e.g., EdTech, FinTech, SaaS)"},
        "target_audience": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Who are their customers?"
        },
        "products": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Main products they SELL (2-5 items)"
        },
        "services": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Professional services they offer"
        },
        "pain_points": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Customer frustrations and problems"
        },
        "customer_problems": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Issues their solution addresses"
        },
        "use_cases": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Real scenarios where product is used"
        },
        "value_propositions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Key value they provide to customers"
        },
        "differentiators": {
            "type": "array",
            "items": {"type": "string"},
            "description": "What makes them unique vs competitors"
        },
        "key_features": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Technical capabilities and features"
        },
        "solution_keywords": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Terms describing their approach/solution"
        },
        "competitors": {
            "type": "array",
            "items": {"type": "string"},
            "description": "3-5 competitor names"
        },
        "brand_voice": {"type": "string", "description": "Communication style (formal/casual, technical/simple)"},
        "product_category": {"type": "string"},
        "primary_region": {"type": "string"}
    },
    "required": ["company_name", "description", "industry", "products"]
}


class CompanyAnalyzer:
    """Analyze company website to extract rich context for keyword generation."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-3-pro-preview"
    ):
        """
        Initialize company analyzer.
        
        Args:
            api_key: Gemini API key (or set GEMINI_API_KEY env var)
            model: Gemini model to use
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY required")
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        
        # Initialize model WITHOUT tools in genai SDK
        # We'll request url reading and search in the prompt instead
        self._model = genai.GenerativeModel(
            model_name=model,
            generation_config=genai.GenerationConfig(
                temperature=0.2,
                response_mime_type="application/json",
                response_schema=COMPANY_ANALYSIS_SCHEMA
            )
        )
        
        logger.info(f"Company Analyzer initialized (model={model})")
    
    async def analyze(self, website_url: str) -> dict:
        """
        Analyze company website to extract rich context.
        
        Args:
            website_url: Company website URL
            
        Returns:
            Dictionary with company analysis:
            - company_name
            - description
            - industry
            - products (what they sell)
            - services
            - pain_points (customer frustrations)
            - customer_problems
            - use_cases
            - value_propositions
            - differentiators
            - key_features
            - solution_keywords
            - competitors
            - brand_voice
            - target_audience
            - product_category
            - primary_region
        """
        logger.info(f"Analyzing company website: {website_url}")
        
        # Get current date for context
        from datetime import datetime
        current_date = datetime.now().strftime("%B %Y")
        
        prompt = f"""Today's date: {current_date}

Analyze the company at {website_url}

IMPORTANT: You have access to browse the web and search Google. Use these capabilities!

STEP 1: Visit and read the website
- Access {website_url} directly
- Read the actual website content
- Extract information about products, services, messaging, brand voice

STEP 2: Search for additional context
- Search: "{website_url} products services"
- Search: "{website_url} customers reviews pain points"  
- Search: "{website_url} vs competitors"
- Search: "{website_url} industry construction"
- Find customer problems, use cases, differentiators

STEP 3: Provide comprehensive company analysis

Focus on extracting SPECIFIC information:
- What do they SELL? (products/services)
- What problems do they SOLVE? (pain points/customer problems)
- What makes them UNIQUE? (differentiators/value props)
- Who are their CUSTOMERS? (target audience)
- Who are their COMPETITORS?
- What is their BRAND VOICE? (formal/casual, technical/simple)
- What INDUSTRY are they in? (be specific!)

Be thorough and specific. Use real information from the website and search results."""

        try:
            import asyncio
            # Run synchronous Gemini call in executor
            response = await asyncio.to_thread(
                self._model.generate_content,
                prompt
            )
            
            # Parse JSON response
            import json
            analysis = json.loads(response.text)
            
            logger.info(f"✅ Company analysis complete: {analysis.get('company_name', 'Unknown')}")
            logger.info(f"   Industry: {analysis.get('industry', 'Unknown')}")
            logger.info(f"   Products: {len(analysis.get('products', []))} found")
            logger.info(f"   Pain points: {len(analysis.get('pain_points', []))} found")
            logger.info(f"   Competitors: {len(analysis.get('competitors', []))} found")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Company analysis failed: {e}")
            raise


async def analyze_company(website_url: str, api_key: Optional[str] = None) -> dict:
    """
    Convenience function to analyze a company website.
    
    Args:
        website_url: Company website URL
        api_key: Optional Gemini API key
        
    Returns:
        Company analysis dictionary
    """
    analyzer = CompanyAnalyzer(api_key=api_key)
    return await analyzer.analyze(website_url)
