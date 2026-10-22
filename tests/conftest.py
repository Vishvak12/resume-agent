from pathlib import Path
import pytest
from resume_agent.profile import load_profile
from resume_agent.skills import load_taxonomy

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture
def profile():
    return load_profile(ROOT / "tests/fixtures/profile/facts.yaml")

@pytest.fixture
def taxonomy():
    return load_taxonomy(ROOT / "data/skills.yaml")
