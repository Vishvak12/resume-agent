from resume_agent.checker import check_resume

def resume_with(bullets, skills=None, positions=None):
    return {
        "experience": positions or [{"org": "Novaport Logistics", "role": "Data Platform Engineering Intern",
                                     "dates": "Jun 2025 – Sep 2025", "bullets": bullets}],
        "skills": skills or [],
    }

def codes(report):
    return {i.code for i in report.issues}

def run(profile, taxonomy, bullets, **kw):
    return check_resume(resume_with(bullets, **kw), profile, taxonomy)

def test_clean_bullet_has_no_issues(profile, taxonomy):
    r = run(profile, taxonomy, [{"text": "Achieved 97% clause recall on dispute audits by fusing BM25 and Hugging Face embeddings, served via FastAPI.", "facts": ["NOVA-RAG"]}])
    assert codes(r) == set()

def test_uncited_bullet_is_citation_missing(profile, taxonomy):
    assert "CITATION_MISSING" in codes(run(profile, taxonomy, ["Built a thing."]))

def test_unknown_fact_id(profile, taxonomy):
    assert "FACT_UNKNOWN" in codes(run(profile, taxonomy, [{"text": "Built a thing.", "facts": ["NOPE-1"]}]))

def test_unconfirmed_and_rejected_facts_fail(profile, taxonomy):
    r = run(profile, taxonomy, [{"text": "Wrote services in Java.", "facts": ["JAVA-X"]},
                                {"text": "Built a Flask backend.", "facts": ["KES-FLASK"]}])
    assert sum(i.code == "FACT_NOT_VERIFIED" for i in r.issues) == 2

def test_number_not_in_cited_facts(profile, taxonomy):
    r = run(profile, taxonomy, [{"text": "Validated the pipeline against 8 labeled invoices.", "facts": ["NOVA-NLP"]}])
    assert "NUMBER_UNSUPPORTED" in codes(r)

def test_number_formats_normalize(profile, taxonomy):
    r = run(profile, taxonomy, [
        {"text": "Validated against 410+ labeled invoices.", "facts": ["NOVA-NLP"]},
        {"text": "Reached 88.41% test accuracy and 0.861 macro F1 on 12,416 features and 812 invoices.", "facts": ["INV-XGB"]}])
    assert "NUMBER_UNSUPPORTED" not in codes(r)

def test_numbers_inside_names_are_ignored(profile, taxonomy):
    r = run(profile, taxonomy, [{"text": "Compared ResNet-18 and 1D-CNN baselines on MT940 statements using SHA-256 hashed S3 objects on EC2.", "facts": ["INV-XGB"]}])
    assert "NUMBER_UNSUPPORTED" not in codes(r)

def test_skill_not_in_cited_facts(profile, taxonomy):
    r = run(profile, taxonomy, [{"text": "Trained the classifier in TensorFlow.", "facts": ["INV-XGB"]}])
    assert "SKILL_UNSUPPORTED" in codes(r)

def test_scope_violation(profile, taxonomy):
    r = run(profile, taxonomy, [{"text": "Deployed the backend on Azure.", "facts": ["NOVA-AZURE"]}])
    assert "SCOPE_VIOLATION" in codes(r)

def test_scoped_skill_within_scope_is_fine(profile, taxonomy):
    r = run(profile, taxonomy, [{"text": "Used Azure for development and testing.", "facts": ["NOVA-AZURE"]}])
    assert "SCOPE_VIOLATION" not in codes(r)

def test_unit_mismatch_warns(profile, taxonomy):
    r = run(profile, taxonomy, [{"text": "Flagged overbilling across 812 carriers.", "facts": ["INV-XGB"]}])
    issue = next(i for i in r.issues if i.code == "UNIT_MISMATCH")
    assert issue.level == "warning"

def test_escalation_word_without_attribute_warns(profile, taxonomy):
    r = run(profile, taxonomy, [{"text": "Built a production retrieval pipeline with FastAPI.", "facts": ["NOVA-RAG"]}])
    assert "ESCALATION_WORD" in codes(r)

def test_escalation_word_with_attribute_is_fine(profile, taxonomy):
    r = run(profile, taxonomy, [{"text": "Built a Node.js backend for a production React Native app with FAISS.", "facts": ["KES-MATCH"]}],
            positions=[{"org": "Kestrel Fleet", "role": "Backend Engineering Intern", "dates": "Jan 2024 – Apr 2024",
                        "bullets": [{"text": "Built a Node.js backend for a production React Native app with FAISS.", "facts": ["KES-MATCH"]}]}])
    assert "ESCALATION_WORD" not in codes(r)

def test_generic_term_in_skills_line(profile, taxonomy):
    assert "SKILLS_GENERIC" in codes(run(profile, taxonomy, [], skills=[["Languages", "Python, Programming"]]))

def test_framework_in_languages_line(profile, taxonomy):
    assert "SKILLS_WRONG_TYPE" in codes(run(profile, taxonomy, [], skills=[["Languages", "Python, PyTorch"]]))

def test_unbacked_skill_in_skills_line(profile, taxonomy):
    assert "SKILLS_UNSUPPORTED" in codes(run(profile, taxonomy, [], skills=[["Languages", "Python, Java"]]))

def test_parenthesized_detail_kept_with_skill(profile, taxonomy):
    r = run(profile, taxonomy, [], skills=[["Search", "FAISS (vector search), RAG"]])
    assert codes(r) == set()

def test_wrong_dates_are_field_mismatch(profile, taxonomy):
    r = run(profile, taxonomy, [], positions=[{"org": "Novaport Logistics", "role": "Data Platform Engineering Intern",
                                               "dates": "Jan 2023 – Mar 2023", "bullets": []}])
    assert "FIELD_MISMATCH" in codes(r)

def test_hyphenated_count_with_wrong_number_is_caught(profile, taxonomy):
    r = run(profile, taxonomy, [{"text": "Passed an 8-invoice acceptance gate.", "facts": ["NOVA-NLP"]}])
    assert "NUMBER_UNSUPPORTED" in codes(r)

def test_hyphenated_count_with_wrong_unit_warns(profile, taxonomy):
    r = run(profile, taxonomy, [{"text": "Flagged overbilling from 812-carrier data.", "facts": ["INV-XGB"]}])
    assert "UNIT_MISMATCH" in codes(r)

def test_hyphenated_count_with_right_unit_is_clean(profile, taxonomy):
    r = run(profile, taxonomy, [{"text": "Modeled 12,416-feature data.", "facts": ["INV-XGB"]}])
    assert codes(r) == set()

def test_metric_names_like_hit_at_1_are_not_numbers(profile, taxonomy):
    r = run(profile, taxonomy, [{"text": "Improved hit@1 with 97% clause recall.", "facts": ["NOVA-RAG"]}])
    assert "NUMBER_UNSUPPORTED" not in codes(r)

def test_fraction_with_unsupported_numbers_is_caught(profile, taxonomy):
    r = run(profile, taxonomy, [{"text": "Reached 6/6 clause recall on dispute audits.", "facts": ["NOVA-RAG"]}])
    assert "NUMBER_UNSUPPORTED" in codes(r)

def test_language_outside_languages_line_warns(profile, taxonomy):
    r = run(profile, taxonomy, [], skills=[["Engineering", "Python, FastAPI"]])
    assert "SKILLS_MIXED_TYPES" in codes(r)

def test_languages_on_their_own_line_is_clean(profile, taxonomy):
    r = run(profile, taxonomy, [], skills=[["Languages", "Python, SQL"], ["Backend", "FastAPI"]])
    assert codes(r) == set()

def test_plain_string_summary_is_uncited(profile, taxonomy):
    r = check_resume({"summary": "Shipped ML systems to 340+ users."}, profile, taxonomy)
    assert "SUMMARY_UNCITED" in codes(r)

def test_cited_summary_sentences_are_checked_like_bullets(profile, taxonomy):
    r = check_resume({"summary": [{"text": "Validated retrieval against 8 labeled invoices.", "facts": ["NOVA-NLP"]}]}, profile, taxonomy)
    assert "NUMBER_UNSUPPORTED" in codes(r)

def test_clean_cited_summary_passes(profile, taxonomy):
    r = check_resume({"summary": [{"text": "Validated an NLP pipeline against 410+ labeled invoices.", "facts": ["NOVA-NLP"]}]}, profile, taxonomy)
    assert codes(r) == set()

def test_profile_years_are_not_metrics(profile, taxonomy):
    r = check_resume({"summary": [{"text": "MS student at Westbridge (Dec 2026) who validated against 410+ labeled invoices.", "facts": ["NOVA-NLP"]}]}, profile, taxonomy)
    assert "NUMBER_UNSUPPORTED" not in codes(r)

def test_unknown_year_is_still_checked(profile, taxonomy):
    r = check_resume({"summary": [{"text": "Built since 2019 a pipeline with 410+ labeled invoices.", "facts": ["NOVA-NLP"]}]}, profile, taxonomy)
    assert "NUMBER_UNSUPPORTED" in codes(r)
