"""Test Pydantic models."""

import pytest
from stage1.stage1_models import Stage1Input, Stage1Output, CompanyContext
from stage4.stage4_models import ScoredKeyword


def test_stage1_input():
    """Test Stage1Input model."""
    input_model = Stage1Input(
        company_url="https://example.com",
        company_name="Example",
    )
    assert input_model.company_url == "https://example.com"
    assert input_model.company_name == "Example"
    assert input_model.language == "en"
    assert input_model.region == "us"


def test_company_context():
    """Test CompanyContext model."""
    context = CompanyContext(
        company_name="Test Co",
        company_url="https://test.com",
        industry="Technology",
    )
    assert context.company_name == "Test Co"
    assert context.products == []
    assert context.services == []


def test_scored_keyword():
    """Test ScoredKeyword model."""
    kw = ScoredKeyword(
        keyword="test keyword",
        intent="informational",
        score=85,
    )
    assert kw.keyword == "test keyword"
    assert kw.score == 85
    assert kw.is_question == False
