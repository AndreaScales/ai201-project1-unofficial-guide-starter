"""Retrieval-backed generator that enforces grounding and programmatic citations.

Usage:
  from generator import answer_with_sources
  answer, sources = answer_with_sources(query, k=5)

This module:
 - retrieves top-k chunks from the persistent Chroma collection
 - constructs a strict prompt for the LLM (via `llm_interface`)
 - calls the LLM to generate an answer (model is expected to follow system prompt)
 - programmatically assigns sentence-level citations by embedding sentences and
   finding the nearest retrieved chunk to guarantee attribution
"""
from typing import List, Dict, Any, Tuple
import numpy as np

from sentence_transformers import SentenceTransformer

try:
    import chromadb
    from chromadb.config import Settings
except Exception:
    chromadb = None

from .llm_interface import build_messages, call_chat


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def _get_chroma_collection(persist_dir: str, collection: str):
    settings = Settings(is_persistent=True, persist_directory=persist_dir)
    client = chromadb.Client(settings=settings)
    coll = client.get_collection(collection)
    return coll


def retrieve_top_k(query: str, k: int = 5, persist_dir: str = "db/chroma", collection: str = "chunks") -> List[Dict[str, Any]]:
    model = SentenceTransformer(MODEL_NAME)
    q_emb = model.encode([query], convert_to_numpy=True)[0].tolist()
    coll = _get_chroma_collection(persist_dir, collection)
    results = coll.query(query_embeddings=[q_emb], n_results=k)
    # results dict has ids, distances, metadatas, documents
    out = []
    ids = results.get("ids", [])[0]
    docs = results.get("documents", [])[0]
    metas = results.get("metadatas", [])[0]
    dists = results.get("distances", [])[0]
    for i, _id in enumerate(ids):
        out.append({"id": _id, "text": docs[i], "metadata": metas[i], "distance": dists[i]})
    return out


def _sentences_from_text(text: str) -> List[str]:
    import re
    s = re.split(r'(?<=[.!?])\s+', text.strip())
    return [x.strip() for x in s if x.strip()]


def embed_texts(texts: List[str], model: SentenceTransformer) -> np.ndarray:
    return model.encode(texts, convert_to_numpy=True)


def assign_citations(answer: str, retrieved: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
    model = SentenceTransformer(MODEL_NAME)
    sents = _sentences_from_text(answer)
    if not sents:
        return answer, []
    sent_embs = embed_texts(sents, model)
    docs = [r["text"] for r in retrieved]
    doc_embs = embed_texts(docs, model)

    # compute cosine similarity
    def cosine(a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10)

    # unique sources mapped to indices
    source_map = {}
    sources = []

    annotated = []
    for i, se in enumerate(sent_embs):
        sims = [cosine(se, de) for de in doc_embs]
        best = int(np.argmax(sims))
        src = retrieved[best]["metadata"].get("source")
        if src not in source_map:
            source_map[src] = len(sources) + 1
            sources.append({"index": source_map[src], "source": src, "metadata": retrieved[best]["metadata"]})
        idx = source_map[src]
        annotated.append((sents[i], idx))

    # rebuild answer with numeric citations
    parts = [f"{sent} [{idx}]" for (sent, idx) in annotated]
    final = " ".join(parts)
    return final, sources


def merge_model_and_programmatic(raw_answer: str, retrieved: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
    """Merge numeric citations produced by the model with programmatic assignment.

    - If the model already places numeric citations like [1], keep them.
    - For sentences missing citations, programmatically find the best-matching
      retrieved chunk and append its numeric index (where indices map to the
      ordering of `retrieved`).
    - Return the final annotated answer and a list of unique sources.
    """
    import re

    raw = raw_answer.strip()
    if not raw:
        return raw, []
    if raw == "I don't know based on the provided sources.":
        return raw, []

    sents = _sentences_from_text(raw)
    if not sents:
        return raw, []

    # build map of model indices -> retrieved entries (1-based)
    idx_to_retr = {i + 1: r for i, r in enumerate(retrieved)}

    # detect which sentences already contain model citations like [1]
    cited_pattern = re.compile(r"\[(\d+)\]")
    sentences_out = []
    # For programmatic fallback, prepare embeddings
    model = SentenceTransformer(MODEL_NAME)
    docs = [r["text"] for r in retrieved]
    doc_embs = embed_texts(docs, model) if docs else None

    # helper similarity
    def cosine(a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10)

    used_indices = []
    # iterate sentences
    for sent in sents:
        found = cited_pattern.findall(sent)
        if found:
            # keep the sentence as-is but record referenced indices
            try:
                for f in found:
                    ni = int(f)
                    if ni in idx_to_retr and ni not in used_indices:
                        used_indices.append(ni)
            except Exception:
                pass
            sentences_out.append(sent)
        else:
            # programmatically assign nearest doc
            if doc_embs is None:
                sentences_out.append(sent)
                continue
            sent_emb = embed_texts([sent], model)[0]
            sims = [cosine(sent_emb, de) for de in doc_embs]
            best = int(np.argmax(sims))
            model_idx = best + 1
            if model_idx not in used_indices:
                used_indices.append(model_idx)
            # append numeric citation
            sentences_out.append(f"{sent} [{model_idx}]")

    # Build sources list in ascending index order (as used in the final answer)
    sources = []
    for ni in sorted(set(used_indices)):
        r = idx_to_retr.get(ni)
        if not r:
            continue
        src = r["metadata"].get("source")
        sources.append({"index": ni, "source": src, "metadata": r.get("metadata", {})})

    final = " ".join(sentences_out)
    return final, sources


def answer_with_sources(query: str, k: int = 5, persist_dir: str = "db/chroma", collection: str = "chunks") -> Dict[str, Any]:
    retrieved = retrieve_top_k(query, k=k, persist_dir=persist_dir, collection=collection)
    # prepare context chunks for LLM
    context_chunks = [{"id": r["id"], "source": r["metadata"].get("source"), "text": r["text"]} for r in retrieved]
    messages = build_messages(query, context_chunks)
    # call LLM
    answer = call_chat(messages)
    # merge model-provided inline citations with programmatic assignment
    annotated_answer, sources = merge_model_and_programmatic(answer, retrieved)

    return {"answer": annotated_answer, "sources": sources, "raw_answer": answer, "retrieved": retrieved}
