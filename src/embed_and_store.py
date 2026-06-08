#!/usr/bin/env python3
"""Embed chunks with sentence-transformers and store in ChromaDB.

Usage examples:
  python3 src/embed_and_store.py --chunks data/chunks.jsonl --persist-dir db/chroma --collection chunks
  python3 src/embed_and_store.py --chunks data/chunks.jsonl --persist-dir db/chroma --collection chunks --test-query "What scholarships exist for HBCU students?"

The script computes embeddings with `sentence-transformers/all-MiniLM-L6-v2` by default
and adds them to a ChromaDB collection with metadata (source, start, end, chunk_index).
If ChromaDB or sentence-transformers is unavailable, the script will raise a helpful error.
"""
import argparse
import json
import os
from pathlib import Path
from typing import List

def load_chunks(path: str) -> List[dict]:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunks", required=True, help="Path to chunks.jsonl")
    parser.add_argument("--persist-dir", default="db/chroma", help="ChromaDB persist directory")
    parser.add_argument("--collection", default="chunks", help="Chroma collection name")
    parser.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2", help="Embedding model")
    parser.add_argument("--test-query", default=None, help="Optional query to run after indexing")
    parser.add_argument("--top-k", type=int, default=4, help="Number of results to return for test query")
    args = parser.parse_args()

    chunks_path = Path(args.chunks)
    assert chunks_path.exists(), f"Chunks file not found: {chunks_path}"

    print(f"Loading chunks from {chunks_path}...")
    chunks = load_chunks(str(chunks_path))
    texts = [r.get("text", "") for r in chunks]
    ids = [r.get("id") or str(i) for i, r in enumerate(chunks)]
    metadatas = []
    for r in chunks:
        md = {
            "source": r.get("source"),
            "start": r.get("start"),
            "end": r.get("end"),
            "chunk_index": r.get("chunk_index"),
        }
        metadatas.append(md)

    # Load embedding model
    try:
        from sentence_transformers import SentenceTransformer
    except Exception as e:
        raise RuntimeError("Please install `sentence-transformers` (see requirements.txt).") from e

    print(f"Loading embedding model {args.model}...")
    model = SentenceTransformer(args.model)

    # Compute embeddings
    print(f"Encoding {len(texts)} chunks (this may take a moment)...")
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)

    # Store in ChromaDB
    try:
        import chromadb
        from chromadb.config import Settings
    except Exception as e:
        raise RuntimeError("Please install `chromadb` (see requirements.txt).") from e

    persist_dir = Path(args.persist_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)

    print(f"Creating Chroma client with persistent dir: {persist_dir}")
    client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory=str(persist_dir)))

    coll = client.get_or_create_collection(name=args.collection)

    # Remove existing ids that collide to allow re-run
    try:
        existing = coll.get(ids=ids)
        if existing and existing.get("ids"):
            print("Removing existing entries with same ids to avoid duplication...")
            coll.delete(ids=ids)
    except Exception:
        # some chroma versions differ; ignore if not supported
        pass

    print(f"Adding {len(ids)} vectors to Chroma collection '{args.collection}'...")
    coll.add(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings.tolist())

    # Persist DB (depends on chroma backend)
    try:
        client.persist()
    except Exception:
        pass

    print("Indexing complete.")

    if args.test_query:
        q = args.test_query
        print(f"Running test retrieval for: {q}")
        q_emb = model.encode([q], convert_to_numpy=True)
        results = coll.query(query_embeddings=q_emb.tolist(), n_results=args.top_k)
        # results is a dict-like object with ids, documents, metadatas, distances
        for i, res_id in enumerate(results.get("ids", [[]])[0]):
            doc = results.get("documents", [[]])[0][i]
            md = results.get("metadatas", [[]])[0][i]
            dist = None
            # chroma may return distances
            dists = results.get("distances")
            if dists:
                try:
                    dist = dists[0][i]
                except Exception:
                    dist = None
            print("---")
            print(f"Rank {i+1} — id={res_id} — distance={dist}")
            print(f"Source: {md.get('source')}")
            print(f"Chunk index: {md.get('chunk_index')}")
            print(doc[:500].replace("\n", " "))


if __name__ == "__main__":
    main()
