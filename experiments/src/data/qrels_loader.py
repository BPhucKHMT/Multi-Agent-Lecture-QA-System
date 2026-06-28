import json
from pathlib import Path
from typing import Any, Dict, List, Union
from experiments.src.qrels.overlap import should_match_evidence
from experiments.src.time_utils import timestamp_to_seconds


class DynamicQueryQrels:
    def __init__(self, evidence_list: list[dict[str, Any]], database_chunks: list[dict[str, Any]]):
        self.evidence_list = evidence_list
        # Index evidence by video_id to avoid scanning the entire evidence list every time
        self.evidence_by_video: dict[str, list[dict[str, Any]]] = {}
        for ev in evidence_list:
            v_id = ev.get("video_id")
            if v_id:
                self.evidence_by_video.setdefault(v_id, []).append(ev)
                
        # Cache for compute_score to avoid redundant string parsing and matching
        self.score_cache: dict[str, int] = {}
        
        # Precompute the set of relevant doc_ids in the database
        self.db_relevant_docs: dict[str, int] = {}
        for chunk in database_chunks:
            doc_id = chunk["doc_id"]
            score = self.compute_score(doc_id)
            if score > 0:
                self.db_relevant_docs[doc_id] = score

    def compute_score(self, doc_id: str) -> int:
        if doc_id in self.score_cache:
            return self.score_cache[doc_id]
            
        try:
            # Parse doc_id: f"{video_id}_{start_seconds}_{end_seconds}"
            # Using rsplit('_', 2) to safely handle video_id containing underscores
            parts = doc_id.rsplit('_', 2)
            if len(parts) != 3:
                self.score_cache[doc_id] = 0
                return 0
            video_id, start_str, end_str = parts
            chunk_start = int(start_str)
            chunk_end = int(end_str)
        except Exception:
            self.score_cache[doc_id] = 0
            return 0

        ev_list = self.evidence_by_video.get(video_id, [])
        if not ev_list:
            self.score_cache[doc_id] = 0
            return 0

        max_score = 0
        for ev in ev_list:
            ev_start = timestamp_to_seconds(ev.get("start_timestamp"))
            ev_end = timestamp_to_seconds(ev.get("end_timestamp"))
            if ev_end <= ev_start:
                continue
            
            if should_match_evidence(ev_start, ev_end, chunk_start, chunk_end):
                score = int(ev.get("score", 1))
                if score > max_score:
                    max_score = score
        self.score_cache[doc_id] = max_score
        return max_score

    def __contains__(self, doc_id: str) -> bool:
        # Check dynamic match first (in case doc_id has different boundaries but overlaps)
        score = self.compute_score(doc_id)
        if score > 0:
            return True
        # fallback to precomputed DB set
        return doc_id in self.db_relevant_docs

    def get(self, doc_id: str, default: int = 0) -> int:
        score = self.compute_score(doc_id)
        if score > 0:
            return score
        return self.db_relevant_docs.get(doc_id, default)

    def __len__(self) -> int:
        # Return the count of matching database chunks
        return len(self.db_relevant_docs)

    def values(self) -> Any:
        return self.db_relevant_docs.values()

    def __bool__(self) -> bool:
        return len(self.db_relevant_docs) > 0 or len(self.evidence_list) > 0


def load_qrels(qrels_path: Union[str, Path]) -> Dict[str, Dict[str, int]]:
    qrels: dict[str, dict[str, int]] = {}
    for line in Path(qrels_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        query_id = record["query_id"]
        doc_id = record["doc_id"]
        relevance = int(record["relevance"])
        qrels.setdefault(query_id, {})[doc_id] = max(
            relevance,
            qrels.get(query_id, {}).get(doc_id, 0),
        )
    return qrels


def load_parent_qrels_from_child_qrels(
    qrels_path: Union[str, Path],
    child_chunks: List[Dict[str, Any]],
) -> Dict[str, Dict[str, int]]:
    child_qrels = load_qrels(qrels_path)
    child_to_parent = {
        chunk["doc_id"]: chunk["metadata"].get("parent_chunk_id")
        for chunk in child_chunks
    }
    parent_qrels: dict[str, dict[str, int]] = {}
    for query_id, docs in child_qrels.items():
        for child_doc_id, relevance in docs.items():
            parent_doc_id = child_to_parent.get(child_doc_id)
            if not parent_doc_id:
                continue
            parent_qrels.setdefault(query_id, {})[parent_doc_id] = max(
                relevance,
                parent_qrels.get(query_id, {}).get(parent_doc_id, 0),
            )
    return parent_qrels


def load_dynamic_qrels(query_path: Union[str, Path], chunks: List[Dict[str, Any]]) -> Dict[str, DynamicQueryQrels]:
    qrels: dict[str, DynamicQueryQrels] = {}
    for line in Path(query_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("category") == "no_answer":
            continue
        query_id = record["id"]
        evidence_list = record.get("evidence", [])
        qrels[query_id] = DynamicQueryQrels(evidence_list, chunks)
    return qrels
