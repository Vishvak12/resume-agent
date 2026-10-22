import pytest
from resume_agent.profile import load_profile, render_facts_md, ProfileError

def test_load_profile_indexes_facts_by_id(profile):
    assert profile.facts["NOVA-RAG"].entity == "Novaport Logistics"

def test_metric_values_are_numbers(profile):
    assert profile.facts["INV-XGB"].metrics[0].value == pytest.approx(88.41)

def test_duplicate_fact_ids_raise(tmp_path):
    p = tmp_path / "facts.yaml"
    p.write_text("facts:\n  - {id: A, entity: x, text: t, status: verified}\n  - {id: A, entity: x, text: t, status: verified}\n")
    with pytest.raises(ProfileError, match="duplicate"):
        load_profile(p)

def test_invalid_status_raises(tmp_path):
    p = tmp_path / "facts.yaml"
    p.write_text("facts:\n  - {id: A, entity: x, text: t, status: maybe}\n")
    with pytest.raises(ProfileError, match="status"):
        load_profile(p)

def test_verified_skills_excludes_unconfirmed_and_rejected(profile):
    skills = profile.verified_skills()
    assert {"Python", "FAISS", "Azure"} <= skills
    assert "Java" not in skills and "Flask" not in skills

def test_render_facts_md_hides_rejected_and_marks_unconfirmed(profile):
    md = render_facts_md(profile)
    assert "[NOVA-RAG]" in md
    assert "KES-FLASK" not in md
    assert "JAVA-X" in md and "do not use" in md.lower()
