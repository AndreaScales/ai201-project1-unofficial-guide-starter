#!/usr/bin/env python3
"""Re-chunk a single source from `data/clean_texts.jsonl` and upsert into Chroma.

Usage:
  python3 src/rechunk_and_add.py --source <URL> --chunk-size 600 --overlap 100

This script:
 - finds the cleaned text for the given source in `data/clean_texts.jsonl`
 - splits into paragraph-aware chunks (target size and overlap)
 - deletes existing chunks in the Chroma collection for that source
 - encodes new chunks and adds them to the collection
"""
import argparse
import hashlib
import json
from pathlib import Path
from typing import List


def load_clean_texts(path: str):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            yield json.loads(line)


def chunk_paragraphs(text: str, chunk_size: int = 600, overlap: int = 100):
    # Split on double-newline; fallback to single newline or sentence boundary
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paras:
        paras = [p.strip() for p in text.split("\n") if p.strip()]
    if not paras:
        paras = [text]

    chunks: List[str] = []
    for p in paras:
        if len(p) <= chunk_size:
            # try to merge into last chunk if it fits
            if chunks and len(chunks[-1]) + len(p) + 2 <= chunk_size:
                chunks[-1] = (chunks[-1] + "\n\n" + p).strip()
            else:
                chunks.append(p)
        else:
            # paragraph too long: split by words into sliding windows
            words = p.split()
            cur_words = []
            cur_len = 0
            i = 0
            while i < len(words):
                w = words[i]
                if cur_len + len(w) + (1 if cur_words else 0) <= chunk_size:
                    cur_words.append(w)
                    cur_len += len(w) + (1 if cur_words else 0)
                    i += 1
                else:
                    if cur_words:
                        chunks.append(" ".join(cur_words))
                    # back up by overlap chars -> approximate by words
                    # compute overlap in words
                    if overlap > 0 and len(chunks) > 0:
                        # determine how many words to carry back
                        carry = []
                        carry_len = 0
                        j = len(cur_words) - 1
                        while j >= 0 and carry_len < overlap:
                            carry_len += len(cur_words[j]) + 1
                            carry.insert(0, cur_words[j])
                            j -= 1
                        # start new window with carry
                        cur_words = carry[:] if carry else []
                        cur_len = sum(len(x) + 1 for x in cur_words) - (1 if cur_words else 0)
                    else:
                        cur_words = []
                        cur_len = 0
            if cur_words:
                chunks.append(" ".join(cur_words))

    # convert to (start,end,text) with character offsets approximate
    final = []
    pos = 0
    for c in chunks:
        s = c
        start = pos
        end = pos + len(s)
        final.append((start, end, s))
        pos = end - overlap if end - overlap > pos else end

    return final


def make_id(source: str, start: int, end: int) -> str:
    h = hashlib.sha1(f"{source}:{start}:{end}".encode()).hexdigest()
    return h[:12]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, help="Source URL to re-chunk")
    parser.add_argument("--cleaned", default="data/clean_texts.jsonl", help="Cleaned texts jsonl")
    parser.add_argument("--chunk-size", type=int, default=600)
    parser.add_argument("--overlap", type=int, default=100)
    parser.add_argument("--persist-dir", default="db/chroma")
    parser.add_argument("--collection", default="chunks")
    args = parser.parse_args()

    source = args.source

    # find cleaned text
    text = None
    for rec in load_clean_texts(args.cleaned):
        if rec.get("source") == source:
            text = rec.get("clean_text") or rec.get("text")
            break
    if not text:
        raise RuntimeError(f"Source not found in {args.cleaned}: {source}")

    # create paragraph-aware chunks
    items = chunk_paragraphs(text, chunk_size=args.chunk_size, overlap=args.overlap)
    docs = []
    metadatas = []
    ids = []
    for idx, (start, end, s) in enumerate(items):
        _id = make_id(source, start, end)
        ids.append(_id)
        docs.append(s)
        metadatas.append({"source": source, "start": start, "end": end, "chunk_index": idx})

    # import embedding model and chroma
    try:
        from sentence_transformers import SentenceTransformer
    except Exception as e:
        raise RuntimeError("Please install sentence-transformers") from e

    try:
        import chromadb
        from chromadb.config import Settings
    except Exception as e:
        raise RuntimeError("Please install chromadb") from e

    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    emb = model.encode(docs, show_progress_bar=True, convert_to_numpy=True)

    settings = Settings(is_persistent=True, persist_directory=str(Path(args.persist_dir)))
    client = chromadb.Client(settings=settings)
    coll = client.get_collection(args.collection)

    # delete existing ids for this source
    try:
        all_data = coll.get()
        existing_ids = []
        for i, md in enumerate(all_data.get("metadatas", [[]])[0]):
            if md and md.get("source") == source:
                existing_ids.append(all_data.get("ids", [[]])[0][i])
        if existing_ids:
            print(f"Deleting {len(existing_ids)} existing chunks for source")
            coll.delete(ids=existing_ids)
    except Exception:
        pass

    print(f"Adding {len(ids)} re-chunked vectors to collection {args.collection}")
    coll.add(ids=ids, documents=docs, metadatas=metadatas, embeddings=emb.tolist())
    try:
        client.persist()
    except Exception:
        pass

    print("Done.")


if __name__ == "__main__":
    main()
