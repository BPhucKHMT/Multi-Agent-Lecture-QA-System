from experiments.src.qrels.overlap import should_match_evidence


def test_overlap_matches_by_seconds_threshold():
    assert should_match_evidence(10, 50, 30, 80) is True


def test_overlap_matches_short_evidence_by_ratio_threshold():
    assert should_match_evidence(100, 106, 103, 109) is True


def test_overlap_rejects_short_evidence_below_ratio_threshold():
    assert should_match_evidence(100, 110, 106, 112) is False


def test_overlap_rejects_non_overlapping_span():
    assert should_match_evidence(10, 20, 20, 30) is False
