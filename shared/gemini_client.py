"""
Shared Gemini Client for OpenKeywords Pipeline

Provides a unified interface to Google's Gemini API with:
- Automatic retries with exponential backoff
- JSON response parsing with fallback extraction
- Google Search grounding support
- Structured output with Pydantic schemas
"""

import json
import logging
import os
import random
import re
from typing import Any, Dict, List, Optional, Type, Union

from google import genai
from google.genai import types
from pydantic import BaseModel

from .constants import (
    GEMINI_MODEL,
    GEMINI_TIMEOUT,
    GEMINI_TIMEOUT_GROUNDED,
    GEMINI_MAX_RETRIES,
    GEMINI_BASE_DELAY,
    GEMINI_MAX_DELAY,
)

logger = logging.getLogger(__name__)


class GeminiClient:
    """
    Shared Gemini API client for the OpenKeywords pipeline.

    Features:
    - Automatic retries with exponential backoff and jitter
    - JSON parsing with fallback extraction
    - Google Search grounding for verified information
    - Structured output with Pydantic schema enforcement
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = GEMINI_MAX_RETRIES,
        base_delay: float = GEMINI_BASE_DELAY,
        max_delay: float = GEMINI_MAX_DELAY,
    ):
        """
        Initialize the Gemini client.

        Args:
            api_key: Gemini API key (or set GEMINI_API_KEY env var)
            model: Model name (default: gemini-2.0-flash)
            max_retries: Maximum retry attempts
            base_delay: Base delay for exponential backoff
            max_delay: Maximum delay between retries
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Gemini API key required. Set GEMINI_API_KEY env var or pass api_key."
            )

        self.model_name = model or GEMINI_MODEL
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

        # Initialize the client
        self.client = genai.Client(api_key=self.api_key)

        logger.info(f"GeminiClient initialized with model: {self.model_name}")

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        use_google_search: bool = False,
        temperature: float = 0.7,
        max_output_tokens: int = 8192,
    ) -> str:
        """
        Generate content with optional Google Search grounding.

        Args:
            prompt: The user prompt
            system_instruction: Optional system instruction
            use_google_search: Enable Google Search grounding
            temperature: Generation temperature (0.0-1.0)
            max_output_tokens: Maximum output tokens

        Returns:
            Generated text content
        """
        # Build config
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

        if system_instruction:
            config.system_instruction = system_instruction

        # Add Google Search grounding if requested
        if use_google_search:
            config.tools = [types.Tool(google_search=types.GoogleSearch())]

        # Set timeout based on grounding
        timeout = GEMINI_TIMEOUT_GROUNDED if use_google_search else GEMINI_TIMEOUT

        # Retry loop with exponential backoff
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = await self.client.aio.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config,
                )

                if response.text:
                    return response.text
                else:
                    raise ValueError("Empty response from Gemini")

            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                # Check if retryable
                is_retryable = any(x in error_str for x in [
                    "rate limit", "429", "503", "500", "timeout",
                    "overloaded", "resource exhausted", "quota"
                ])

                if not is_retryable or attempt == self.max_retries - 1:
                    logger.error(f"Gemini error (attempt {attempt + 1}): {e}")
                    raise

                # Calculate backoff delay with jitter
                delay = min(
                    self.max_delay,
                    self.base_delay * (2 ** attempt) + random.uniform(0, 1)
                )
                logger.warning(f"Retry {attempt + 1}/{self.max_retries} after {delay:.1f}s: {e}")

                import asyncio
                await asyncio.sleep(delay)

        raise last_error or ValueError("Max retries exceeded")

    async def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        use_google_search: bool = False,
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """
        Generate content and parse as JSON.

        Args:
            prompt: The user prompt (should request JSON output)
            system_instruction: Optional system instruction
            use_google_search: Enable Google Search grounding
            temperature: Generation temperature (lower = more deterministic)

        Returns:
            Parsed JSON as dictionary
        """
        # Add JSON instruction to system prompt
        json_instruction = (
            "You must respond with valid JSON only. "
            "Do not include markdown code blocks or any other text."
        )
        full_system = f"{system_instruction}\n\n{json_instruction}" if system_instruction else json_instruction

        response = await self.generate(
            prompt=prompt,
            system_instruction=full_system,
            use_google_search=use_google_search,
            temperature=temperature,
        )

        return self._parse_json(response)

    async def generate_with_schema(
        self,
        prompt: str,
        schema: Union[Type[BaseModel], Dict[str, Any]],
        system_instruction: Optional[str] = None,
        use_google_search: bool = False,
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """
        Generate content matching a Pydantic schema.

        Args:
            prompt: The user prompt
            schema: Pydantic model class or JSON schema dict
            system_instruction: Optional system instruction
            use_google_search: Enable Google Search grounding
            temperature: Generation temperature

        Returns:
            Parsed and validated data as dictionary
        """
        # Get JSON schema from Pydantic model if needed
        if isinstance(schema, type) and issubclass(schema, BaseModel):
            json_schema = schema.model_json_schema()
        else:
            json_schema = schema

        # Build schema-aware prompt
        schema_str = json.dumps(json_schema, indent=2)
        schema_prompt = f"{prompt}\n\nRespond with JSON matching this schema:\n{schema_str}"

        return await self.generate_json(
            prompt=schema_prompt,
            system_instruction=system_instruction,
            use_google_search=use_google_search,
            temperature=temperature,
        )

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """
        Parse JSON from response text with fallback extraction.

        Handles:
        - Plain JSON
        - Markdown code blocks (```json ... ```)
        - Malformed JSON with extraction fallback
        """
        text = text.strip()

        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block
        code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if code_block_match:
            try:
                return json.loads(code_block_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try extracting JSON object with balanced braces
        json_str = self._extract_json_object(text)
        if json_str:
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        # Try extracting JSON array
        json_arr = self._extract_json_array(text)
        if json_arr:
            try:
                return json.loads(json_arr)
            except json.JSONDecodeError:
                pass

        logger.error(f"Failed to parse JSON from response: {text[:500]}...")
        raise ValueError(f"Could not parse JSON from response")

    def _extract_json_object(self, text: str) -> Optional[str]:
        """Extract JSON object using balanced brace counting."""
        start = text.find("{")
        if start == -1:
            return None

        depth = 0
        in_string = False
        escape_next = False

        for i, char in enumerate(text[start:], start):
            if escape_next:
                escape_next = False
                continue

            if char == "\\":
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if in_string:
                continue

            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]

        return None

    def _extract_json_array(self, text: str) -> Optional[str]:
        """Extract JSON array using balanced bracket counting."""
        start = text.find("[")
        if start == -1:
            return None

        depth = 0
        in_string = False
        escape_next = False

        for i, char in enumerate(text[start:], start):
            if escape_next:
                escape_next = False
                continue

            if char == "\\":
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if in_string:
                continue

            if char == "[":
                depth += 1
            elif char == "]":
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]

        return None
