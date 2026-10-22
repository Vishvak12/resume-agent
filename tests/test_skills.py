def names(matches):
    return {m.canonical for m in matches}

def test_alias_maps_to_canonical(taxonomy):
    assert taxonomy.lookup("JS").canonical == "JavaScript"
    assert taxonomy.lookup("Postgres").canonical == "PostgreSQL"

def test_programming_is_generic(taxonomy):
    assert taxonomy.lookup("programming").type == "generic"

def test_unknown_term_returns_none(taxonomy):
    assert taxonomy.lookup("Quixotic9000") is None

def test_match_finds_skills_in_text(taxonomy):
    assert names(taxonomy.match("Trained a policy in PyTorch and served results with FAISS")) == {"PyTorch", "FAISS"}

def test_longest_match_wins(taxonomy):
    assert names(taxonomy.match("a production React Native app")) == {"React Native"}

def test_ambiguous_go_requires_exact_case(taxonomy):
    assert names(taxonomy.match("willing to go above and beyond")) == set()
    assert names(taxonomy.match("services in Go and Kubernetes")) == {"Go", "Kubernetes"}
