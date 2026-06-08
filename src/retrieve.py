#!/usr/bin/env python3
"""Query the persistent ChromaDB and return top-k chunks with metadata.

Usage:
  python3 src/retrieve.py --query "What scholarships exist for HBCU students?" --k 4

This script computes an embedding for the query using `sentence-transformers/all-MiniLM-L6-v2`
and queries the persistent ChromaDB located at `--persist-dir` and collection `--collection`.
It prints ranked results with id, distance, source, chunk_index and a short snippet.
"""
import argparse
import json
from pathlib import Path
from typing import List, Dict


def retrieve(query: str, k: int = 4, persist_dir: str = "db/chroma", collection: str = "chunks", model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> List[Dict]:
    try:
        from sentence_transformers import SentenceTransformer
    except Exception as e:
        raise RuntimeError("Please install `sentence-transformers` to run retrieval.") from e

    try:
        import chromadb
        from chromadb.config import Settings
    except Exception as e:
        raise RuntimeError("Please install `chromadb` to run retrieval.") from e

    # Load embedding model
    model = SentenceTransformer(model_name)
    q_emb = model.encode([query], convert_to_numpy=True)

    # Open persistent Chroma client
    persist_path = Path(persist_dir)
    if not persist_path.exists():
        raise RuntimeError(f"Chroma persist directory not found: {persist_dir}")

    settings = Settings(is_persistent=True, persist_directory=str(persist_path))
    client = chromadb.Client(settings=settings)
    coll = client.get_collection(collection)

    results = coll.query(query_embeddings=q_emb.tolist(), n_results=k)

    ids = results.get("ids", [[]])[0]
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    dists = results.get("distances", [[]])[0] if results.get("distances") else [None] * len(ids)

    out = []
    for i, _id in enumerate(ids):
        md = metas[i] if i < len(metas) else {}
        doc = docs[i] if i < len(docs) else ""
        dist = dists[i] if i < len(dists) else None
        out.append({
            "rank": i + 1,
            "id": _id,
            "distance": dist,
            "source": md.get("source"),
            "chunk_index": md.get("chunk_index"),
            "start": md.get("start"),
            "end": md.get("end"),
            "text": doc,
        })

    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True, help="Query string")
    parser.add_argument("--k", type=int, default=4, help="Top-k to retrieve")
    parser.add_argument("--persist-dir", default="db/chroma", help="Chroma persist dir")
    parser.add_argument("--collection", default="chunks", help="Chroma collection name")
    parser.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2", help="Embedding model to use for the query")
    parser.add_argument("--json", action="store_true", help="Output full results as JSON")
    args = parser.parse_args()

    res = retrieve(args.query, k=args.k, persist_dir=args.persist_dir, collection=args.collection, model_name=args.model)

    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    for r in res:
        print("---")
        print(f"Rank {r['rank']} — id={r['id']} — distance={r['distance']}")
        print(f"Source: {r['source']}")
        print(f"Chunk index: {r['chunk_index']} start={r.get('start')} end={r.get('end')}")
        snippet = r['text'][:500].replace("\n", " ")
        print(snippet)


if __name__ == "__main__":
    main()
