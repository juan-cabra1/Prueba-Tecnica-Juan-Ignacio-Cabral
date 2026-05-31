def test_in_scope_cases_not_empty():
    from tests.eval.cases import IN_SCOPE_CASES
    assert len(IN_SCOPE_CASES) >= 6


def test_out_of_scope_cases_not_empty():
    from tests.eval.cases import OUT_OF_SCOPE_CASES
    assert len(OUT_OF_SCOPE_CASES) >= 2


def test_out_of_scope_cases_include_required_examples():
    """The two out-of-scope queries from the problem statement must be present."""
    from tests.eval.cases import OUT_OF_SCOPE_CASES
    queries = [c.query for c in OUT_OF_SCOPE_CASES]
    assert any("502" in q for q in queries), "Must include the error 502 case"
    assert any("autenticación" in q.lower() for q in queries), "Must include the restart auth service case"


def test_in_scope_known_codigos_are_valid():
    """Cases with expected_codigo must use real codes from the corpus."""
    from tests.eval.cases import IN_SCOPE_CASES
    known_codes = {"ERR-DB-001", "ERR-CAT-001", "ERR-AUTH-001"}
    for case in IN_SCOPE_CASES:
        if case.expected_codigo is not None:
            assert case.expected_codigo in known_codes, f"Unknown code: {case.expected_codigo}"
