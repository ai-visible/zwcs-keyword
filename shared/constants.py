"""
OpenKeywords Constants

Shared configuration values for the keyword generation pipeline.
"""

import os

# =============================================================================
# Gemini Configuration
# =============================================================================

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_TIMEOUT = int(os.getenv("GEMINI_TIMEOUT", "120"))
GEMINI_TIMEOUT_GROUNDED = int(os.getenv("GEMINI_TIMEOUT_GROUNDED", "180"))
GEMINI_MAX_RETRIES = int(os.getenv("GEMINI_MAX_RETRIES", "4"))
GEMINI_BASE_DELAY = float(os.getenv("GEMINI_BASE_DELAY", "1.0"))
GEMINI_MAX_DELAY = float(os.getenv("GEMINI_MAX_DELAY", "30.0"))

# =============================================================================
# Keyword Generation
# =============================================================================

VALID_INTENTS = {
    "transactional",
    "commercial",
    "comparison",
    "informational",
    "question",
}

# Broad keyword patterns to filter in research focus mode
BROAD_PATTERNS = [
    r"^what is \w+$",      # "what is AEO" - too basic
    r"^\w+ vs \w+$",       # "AEO vs SEO" - too broad
    r"^best \w+$",         # "best tools" - too generic
    r"^top \w+$",          # "top companies" - too generic
    r"^\w+ guide$",        # "AEO guide" - too basic
    r"^\w+ definition$",   # "X definition"
    r"^\w+ meaning$",      # "X meaning"
]

# =============================================================================
# Pipeline Defaults
# =============================================================================

DEFAULT_TARGET_COUNT = 50
DEFAULT_MIN_SCORE = 40
DEFAULT_CLUSTER_COUNT = 6
DEFAULT_LANGUAGE = "english"
DEFAULT_REGION = "us"

# =============================================================================
# Research Sources
# =============================================================================

RESEARCH_PLATFORMS = ["reddit", "quora", "forum", "blog"]
MAX_RESEARCH_SOURCES_PER_KEYWORD = 5
