#!/usr/bin/env python3
"""Simple ingestion and chunking script for Project 1.

Usage:
  python3 src/ingest.py --test
  python3 src/ingest.py --sources data/sources.json --out data/chunks.jsonl

This script is intentionally dependency-light for the test path.
"""
import argparse
import json
import os
import re
import hashlib
from pathlib import Path


def clean_html(html: str) -> str:
    """Clean HTML and remove navigation/footer boilerplate when possible."""
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        # remove common boilerplate containers
        for sel in ["nav", "header", "footer", "aside", ".sidebar", ".nav", "#nav", "#header", "#footer"]:
            for el in soup.select(sel):
                el.decompose()
        # remove scripts/styles
        for s in soup(["script", "style"]):
            s.decompose()
        text = soup.get_text(separator="\n")
        return text
    except Exception:
        # Fallback: strip tags roughly
        text = re.sub(r"<script.*?>.*?</script>", "", html, flags=re.S)
        text = re.sub(r"<style.*?>.*?</style>", "", text, flags=re.S)
        text = re.sub(r"<[^>]+>", "", text)
        return text


def normalize_whitespace(text: str) -> str:
    return re.sub(r"[\t\r ]+", " ", text).strip()


def chunk_text(text: str, source: str, chunk_size: int = 1000, overlap: int = 150):
    """Split text into chunks of approximately `chunk_size` characters with `overlap`.

    Returns list of dicts: {id, source, text, start, end}
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = normalize_whitespace(text)
    chunks = []
    start = 0
    length = len(text)
    i = 0
    while start < length:
        end = min(start + chunk_size, length)
        chunk_text = text[start:end]
        # expand to nearest sentence end if possible (avoid chopping mid-sentence)
        if end < length:
            window_start = max(end - 50, start)
            m = re.search(r"[\.\!\?]\s", text[window_start : min(end + 200, length)])
            if m:
                adj = window_start + m.end()
                if adj > end:
                    end = adj
                    chunk_text = text[start:end]

        chunk_id = hashlib.sha1(f"{source}:{start}:{end}".encode()).hexdigest()[:12]
        chunks.append({
            "id": chunk_id,
            "source": source,
            "text": chunk_text.strip(),
            "start": start,
            "end": end,
            "chunk_index": i,
        })
        i += 1
        if end < length:
            new_start = end - overlap
            if new_start <= start:
                # fallback to advancing to end to avoid infinite loop
                start = end
            else:
                start = new_start
        else:
            start = end
    return chunks


def load_local_documents(folder: Path):
    docs = []
    if not folder.exists():
        return docs
    for p in folder.rglob("*"):
        if p.is_file():
            if p.suffix.lower() in {".md", ".txt", ".html", ".htm"}:
                text = p.read_text(encoding="utf8", errors="ignore")
                if p.suffix.lower() in {".html", ".htm"}:
                    text = clean_html(text)
                docs.append((str(p), text))
    return docs


def save_chunks(chunks, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf8") as fh:
        for c in chunks:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", default="data/sources.json")
    parser.add_argument("--out", default="data/chunks.jsonl")
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--overlap", type=int, default=150)
    parser.add_argument("--cleaned", default=None, help="Path to cleaned JSONL (data/clean_texts.jsonl) to chunk instead of raw/fetching")
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--fetch", action="store_true", help="Fetch remote URLs listed in --sources")
    args = parser.parse_args()

    out_path = Path(args.out)

    all_chunks = []

    if args.test:
        # create sample text and chunk it
        sample = (
            "Study abroad can be transformative. This sample text will be split into "
            "chunks by the ingestion script. It includes multiple sentences so we can "
            "validate that chunk boundaries prefer sentence ends when possible."
        ) * 6
        chunks = chunk_text(sample, source="__test__", chunk_size=args.chunk_size, overlap=args.overlap)
        save_chunks(chunks, Path("data/chunks_test.jsonl"))
        print(f"Wrote {len(chunks)} chunks to data/chunks_test.jsonl")
        return

    # load local documents
    # If a cleaned JSONL is provided, prefer chunking that cleaned text
    if args.cleaned:
        cleaned_path = Path(args.cleaned)
        if cleaned_path.exists():
            with cleaned_path.open("r", encoding="utf8") as fh:
                for line in fh:
                    try:
                        obj = json.loads(line)
                        src = obj.get("source") or obj.get("id")
                        text = obj.get("clean_text") or obj.get("text") or ""
                        if not text:
                            # skip empty entries but keep placeholder
                            all_chunks.append({
                                "id": hashlib.sha1(f"{src}".encode()).hexdigest()[:12],
                                "source": src,
                                "text": "",
                                "start": 0,
                                "end": 0,
                                "chunk_index": 0,
                            })
                            continue
                        chunks = chunk_text(text, source=src, chunk_size=args.chunk_size, overlap=args.overlap)
                        all_chunks.extend(chunks)
                    except Exception:
                        continue
        else:
            print(f"Cleaned file {cleaned_path} not found; falling back to local documents.")
            local_docs = load_local_documents(Path("documents"))
            for path, text in local_docs:
                chunks = chunk_text(text, source=path, chunk_size=args.chunk_size, overlap=args.overlap)
                all_chunks.extend(chunks)
    else:
        local_docs = load_local_documents(Path("documents"))
        for path, text in local_docs:
            chunks = chunk_text(text, source=path, chunk_size=args.chunk_size, overlap=args.overlap)
            all_chunks.extend(chunks)

    # load external sources list (just urls)
    try:
        with open(args.sources, "r", encoding="utf8") as fh:
            sources = json.load(fh)
    except Exception:
        sources = []

    # optionally fetch remote sources and chunk them
    if args.fetch:
        headers = {"User-Agent": "ai201-ingest/1.0 (+https://github.com)"}
        # prefer requests if available, otherwise fallback to urllib
        try:
            import requests

            def fetch_url(url):
                r = requests.get(url, timeout=10, headers=headers)
                r.raise_for_status()
                return r.text
        except Exception:
            import urllib.request

            def fetch_url(url):
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return resp.read().decode(errors="ignore")

        for s in sources:
            try:
                body = fetch_url(s)
                if body:
                    text = clean_html(body)
                    text = normalize_whitespace(text)
                    chunks = chunk_text(text, source=s, chunk_size=args.chunk_size, overlap=args.overlap)
                    all_chunks.extend(chunks)
                else:
                    all_chunks.append({
                        "id": hashlib.sha1(f"{s}".encode()).hexdigest()[:12],
                        "source": s,
                        "text": "",
                        "start": 0,
                        "end": 0,
                        "chunk_index": 0,
                    })
            except Exception as e:
                all_chunks.append({
                    "id": hashlib.sha1(f"{s}".encode()).hexdigest()[:12],
                    "source": s,
                    "text": "",
                    "start": 0,
                    "end": 0,
                    "chunk_index": 0,
                    "error": str(e),
                })
    else:
        # embed metadata about external sources but do not fetch by default
        for s in sources:
            all_chunks.append({
                "id": hashlib.sha1(f"{s}".encode()).hexdigest()[:12],
                "source": s,
                "text": "",  # placeholder; fetching remote content is optional
                "start": 0,
                "end": 0,
                "chunk_index": 0,
            })

    save_chunks(all_chunks, out_path)
    print(f"Wrote {len(all_chunks)} chunks to {out_path}")


if __name__ == "__main__":
    main()
