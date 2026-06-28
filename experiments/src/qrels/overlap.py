SHORT_EVIDENCE_SECONDS = 15
MIN_OVERLAP_SECONDS = 15
MIN_OVERLAP_RATIO = 0.3
MIN_SHORT_OVERLAP_RATIO = 0.5


def should_match_evidence(
    evidence_start: int,
    evidence_end: int,
    chunk_start: int,
    chunk_end: int,
) -> bool:
    evidence_len = evidence_end - evidence_start
    if evidence_len <= 0 or chunk_end <= chunk_start:
        return False

    overlap_start = max(evidence_start, chunk_start)
    overlap_end = min(evidence_end, chunk_end)
    overlap_seconds = overlap_end - overlap_start
    if overlap_seconds <= 0:
        return False

    overlap_ratio = overlap_seconds / evidence_len
    if evidence_len < SHORT_EVIDENCE_SECONDS:
        return overlap_ratio >= MIN_SHORT_OVERLAP_RATIO
    return overlap_seconds >= MIN_OVERLAP_SECONDS or overlap_ratio >= MIN_OVERLAP_RATIO
