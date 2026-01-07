"""Test that all modules import correctly."""

import pytest


def test_api_imports():
    """Test API module imports."""
    from api import app
    assert app is not None


def test_pipeline_imports():
    """Test pipeline imports."""
    from run_pipeline import run_pipeline
    assert run_pipeline is not None


def test_stage1_imports():
    """Test stage1 imports."""
    from stage1 import run_stage_1, Stage1Input, Stage1Output
    assert run_stage_1 is not None


def test_stage2_imports():
    """Test stage2 imports."""
    from stage2 import run_stage_2, Stage2Input, Stage2Output
    assert run_stage_2 is not None


def test_stage3_imports():
    """Test stage3 imports."""
    from stage3 import run_stage_3, Stage3Input, Stage3Output
    assert run_stage_3 is not None


def test_stage4_imports():
    """Test stage4 imports."""
    from stage4 import run_stage_4, Stage4Input, Stage4Output
    assert run_stage_4 is not None


def test_stage5_imports():
    """Test stage5 imports."""
    from stage5 import run_stage_5, Stage5Input, Stage5Output
    assert run_stage_5 is not None
