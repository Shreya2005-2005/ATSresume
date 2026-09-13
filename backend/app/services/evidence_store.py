"""Candidate Evidence Store — the single source of truth for the pipeline.

Every evidence unit is embedded into a persistent ChromaDB collection.
No downstream stage is permitted to assert a claim that cannot be
retrieved from here.
"""
import json
import threading
import uuid
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

from app.core.config import CHROMA_DIR, EVIDENCE_DIR
from app.models.evidence import EvidenceUnit

COLLECTION_NAME = "candidate_evidence"

ID_PREFIXES = {
    "work_experience": "work",
    "project": "proj",
    "open_source_pr": "oss",
    "education": "edu",
    "certification": "cert",
    "skill_note": "skill",
    "achievement": "achv",
}

_client = None
_collection = None
_embedding_fn = embedding_functions.DefaultEmbeddingFunction()
_lock = threading.RLock()


def get_client():
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return _client


def get_collection(reset: bool = False):
    global _collection
    client = get_client()
    with _lock:
        if reset:
            try:
                client.delete_collection(COLLECTION_NAME)
            except Exception:
                pass
            _collection = None
        if _collection is None:
            _collection = client.get_or_create_collection(
                name=COLLECTION_NAME,
                embedding_function=_embedding_fn,
                metadata={"hnsw:space": "cosine"},
            )
        return _collection


def load_evidence_file(path: Path) -> list[EvidenceUnit]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return [EvidenceUnit(**item) for item in raw]


def ingest_evidence(units: list[EvidenceUnit], reset: bool = True) -> int:
    # Reset + add must be atomic relative to other resets: two concurrent
    # ingest-default calls (e.g. two open tabs) could otherwise each delete
    # and recreate the collection in turn, leaving an earlier call's `add`
    # pointed at a collection id that a later reset already deleted.
    # _lock is an RLock so this nested acquisition (get_collection also
    # locks) doesn't deadlock.
    with _lock:
        collection = get_collection(reset=reset)
        if not units:
            return 0
        collection.add(
            ids=[u.id for u in units],
            documents=[u.to_document() for u in units],
            metadatas=[u.to_metadata() for u in units],
        )
        return len(units)


def ingest_default_evidence(reset: bool = True) -> int:
    path = EVIDENCE_DIR / "candidate_evidence.json"
    units = load_evidence_file(path)
    return ingest_evidence(units, reset=reset)


def next_evidence_id(evidence_type: str) -> str:
    prefix = ID_PREFIXES.get(evidence_type, "ev")
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def add_evidence_unit(unit: EvidenceUnit) -> None:
    """Adds one candidate-submitted evidence unit, persisting it to the
    evidence file (so it survives a future ingest-default reset) and to
    the live collection (so it's queryable immediately)."""
    path = EVIDENCE_DIR / "candidate_evidence.json"
    existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    existing.append(unit.model_dump())
    path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    ingest_evidence([unit], reset=False)


def delete_evidence_unit(evidence_id: str) -> bool:
    """Removes one evidence unit from both the persisted file and the live
    collection. Returns False if no such id existed."""
    path = EVIDENCE_DIR / "candidate_evidence.json"
    existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    remaining = [item for item in existing if item.get("id") != evidence_id]
    if len(remaining) == len(existing):
        return False
    path.write_text(json.dumps(remaining, indent=2), encoding="utf-8")
    collection = get_collection()
    collection.delete(ids=[evidence_id])
    return True


def query_evidence(query_text: str, top_k: int = 5) -> list[dict]:
    collection = get_collection()
    results = collection.query(query_texts=[query_text], n_results=top_k)
    matches = []
    ids = results["ids"][0]
    docs = results["documents"][0]
    metas = results["metadatas"][0]
    dists = results["distances"][0]
    for i in range(len(ids)):
        # cosine distance -> similarity confidence in [0, 1]
        confidence = max(0.0, 1.0 - dists[i] / 2.0)
        matches.append(
            {
                "evidence_id": ids[i],
                "document": docs[i],
                "metadata": metas[i],
                "confidence": round(confidence, 4),
            }
        )
    return matches


def get_all_evidence() -> list[dict]:
    collection = get_collection()
    result = collection.get()
    out = []
    for i, eid in enumerate(result["ids"]):
        out.append({"evidence_id": eid, "document": result["documents"][i], "metadata": result["metadatas"][i]})
    return out


def get_by_ids(ids: list[str]) -> list[dict]:
    if not ids:
        return []
    collection = get_collection()
    result = collection.get(ids=ids)
    out = []
    for i, eid in enumerate(result["ids"]):
        out.append({"evidence_id": eid, "document": result["documents"][i], "metadata": result["metadatas"][i]})
    return out
